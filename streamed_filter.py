import asyncio
import re
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright

logging.basicConfig(
    filename="scrape.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%H:%M:%S"))
logging.getLogger("").addHandler(console)
log = logging.getLogger("scraper")

CUSTOM_HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

# 🎯 CATEGORY FILTER
ALLOWED_CATEGORIES = ["football", "basketball"]

FALLBACK_LOGOS = {
    "american football": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/nfl.png?raw=true",
    "football": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/football.png?raw=true",
    "fight": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/mma.png?raw=true",
    "basketball": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/nba.png?raw=true",
    "motor sports": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/f1.png?raw=true",
    "darts": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/darts2.png?raw=true",
    "tennis": "http://drewlive24.duckdns.org:9000/Logos/Tennis-2.png",
    "rugby": "http://drewlive24.duckdns.org:9000/Logos/Rugby.png",
    "cricket": "http://drewlive24.duckdns.org:9000/Logos/Cricket.png",
    "golf": "http://drewlive24.duckdns.org:9000/Logos/Golf.png",
    "other": "http://drewlive24.duckdns.org:9000/Logos/DrewLiveSports.png"
}

TV_IDS = {
    "football": "Soccer.Dummy.us",
    "basketball": "Basketball.Dummy.us",
    "american football": "Football.Dummy.us",
    "other": "Sports.Dummy.us"
}

total_matches = 0
total_embeds = 0
total_streams = 0
total_failures = 0


def strip_non_ascii(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[^\x00-\x7F]+", "", text)


def get_all_matches():
    """Fetch & filter only football + basketball"""
    endpoints = ["live"]
    filtered = []

    for ep in endpoints:
        try:
            log.info(f"📡 Fetching {ep} matches...")
            res = requests.get(f"https://streami.su/api/matches/{ep}", timeout=10)
            res.raise_for_status()
            data = res.json()

            # 🎯 FILTER HERE
            only_allowed = [
                m for m in data
                if m.get("category", "").lower() in ALLOWED_CATEGORIES
            ]

            log.info(f"🎯 Filtered ({ep}): {len(only_allowed)} matches")

            filtered.extend(only_allowed)

        except Exception as e:
            log.warning(f"⚠️ Failed fetching {ep}: {e}")

    log.info(f"🎯 Total filtered matches: {len(filtered)}")
    return filtered


def get_embed_urls_from_api(source):
    try:
        s_name, s_id = source.get("source"), source.get("id")
        if not s_name or not s_id:
            return []
        res = requests.get(f"https://streami.su/api/stream/{s_name}/{s_id}", timeout=6)
        res.raise_for_status()
        data = res.json()
        return [d.get("embedUrl") for d in data if d.get("embedUrl")]
    except Exception:
        return []


async def extract_m3u8(page, embed_url):
    global total_failures
    found = None
    try:
        async def on_request(request):
            nonlocal found
            if ".m3u8" in request.url and not found:
                if "prd.jwpltx.com" in request.url:
                    return
                found = request.url
                log.info(f"  ⚡ Stream: {found}")

        page.on("request", on_request)
        await page.goto(embed_url, wait_until="domcontentloaded", timeout=5000)
        await page.mouse.click(200, 200)
        await asyncio.sleep(1)

        return found
    except:
        total_failures += 1
        return None


def validate_logo(url, category):
    cat = (category or "other").lower().replace("-", " ").strip()
    fallback = FALLBACK_LOGOS.get(cat, FALLBACK_LOGOS["other"])
    if url:
        try:
            res = requests.head(url, timeout=2)
            if res.status_code in (200, 302):
                return url
        except:
            pass
    return fallback


def build_logo_url(match):
    cat = (match.get("category") or "other").strip().lower()
    return FALLBACK_LOGOS.get(cat, FALLBACK_LOGOS["other"]), cat


async def process_match(index, match, total, ctx):
    global total_embeds, total_streams
    title = strip_non_ascii(match.get("title", "Unknown Match"))
    log.info(f"\n🎯 [{index}/{total}] {title}")

    sources = match.get("sources", [])
    page = await ctx.new_page()

    for s in sources:
        embed_urls = get_embed_urls_from_api(s)
        total_embeds += len(embed_urls)

        for embed in embed_urls:
            m3u8 = await extract_m3u8(page, embed)
            if m3u8:
                total_streams += 1
                await page.close()
                return match, m3u8

    await page.close()
    return match, None


async def generate_playlist():
    global total_matches
    matches = get_all_matches()
    total_matches = len(matches)

    if not matches:
        return "#EXTM3U\n"

    content = ["#EXTM3U"]
    success = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(extra_http_headers=CUSTOM_HEADERS)

        for i, m in enumerate(matches, 1):
            match, url = await process_match(i, m, len(matches), ctx)
            if not url:
                continue

            logo, cat = build_logo_url(match)
            tv_id = TV_IDS.get(cat, TV_IDS["other"])
            title = strip_non_ascii(match.get("title", "Untitled"))

            content.append(
                f'#EXTINF:-1 tvg-id="{tv_id}" tvg-name="{title}" '
                f'tvg-logo="{logo}" group-title="StreamedSU - {cat.title()}",{title}'
            )
            content.append(url)

            success += 1

        await browser.close()

    log.info(f"🎉 {success} streams OK")
    return "\n".join(content)


if __name__ == "__main__":
    start = datetime.now()
    playlist = asyncio.run(generate_playlist())
    with open("StreamedSU_FILTERED.m3u8", "w") as f:
        f.write(playlist)
    log.info("🎯 DONE")
