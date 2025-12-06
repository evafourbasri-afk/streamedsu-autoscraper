import asyncio
import re
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright

logging.basicConfig(
    filename="scrape_filtered.log",
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

FALLBACK_LOGOS = {
    "football": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/football.png?raw=true",
    "basketball": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/nba.png?raw=true",
    "american football": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/nfl.png?raw=true",
    "other": "http://drewlive24.duckdns.org:9000/Logos/DrewLiveSports.png"
}

TV_IDS = {
    "football": "Soccer.Dummy.us",
    "basketball": "Basketball.Dummy.us",
    "american football": "Football.Dummy.us",
    "other": "Sports.Dummy.us",
}

# ⚠️ CATEGORY YANG DIIZINKAN (HANYA INI!)
ALLOWED = {"football", "basketball"}

total_matches = 0
total_embeds = 0
total_streams = 0
total_failures = 0


def strip_non_ascii(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[^\x00-\x7F]+", "", text)


def get_all_matches():
    try:
        res = requests.get("https://streami.su/api/matches/live", timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        log.error(f"❌ Failed to fetch matches: {e}")
        return []

    filtered = []

    for m in data:
        cat = (m.get("category") or "").lower().strip().replace("-", " ")
        if cat in ALLOWED:
            filtered.append(m)

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
                log.info(f"  ⚡ Found Stream: {found}")

        page.on("request", on_request)

        await page.goto(embed_url, wait_until="domcontentloaded", timeout=5000)

        selectors = [
            "div.jw-icon-display", ".jw-icon-playback", ".vjs-big-play-button",
            ".plyr__control", "div[class*='play']", "button", "canvas"
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click(timeout=300)
                    break
            except:
                continue

        await asyncio.sleep(1)

        return found

    except Exception as e:
        total_failures += 1
        log.warning(f"⚠️ Failed extracting stream: {e}")
        return None


def validate_logo(url, category):
    cat = category.lower().strip()
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
    teams = match.get("teams") or {}
    for side in ["away", "home"]:
        badge = teams.get(side, {}).get("badge")
        if badge:
            url = f"https://streami.su/api/images/badge/{badge}.webp"
            return validate_logo(url, cat), cat
    if match.get("poster"):
        url = f"https://streami.su/api/images/proxy/{match['poster']}.webp"
        return validate_logo(url, cat), cat

    return validate_logo(None, cat), cat


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
    matches = get_all_matches()
    total = len(matches)

    if total == 0:
        return "#EXTM3U\n"

    content = ["#EXTM3U"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome-beta")
        ctx = await browser.new_context(extra_http_headers=CUSTOM_HEADERS)

        sem = asyncio.Semaphore(2)

        async def worker(i, m):
            async with sem:
                return await process_match(i, m, total, ctx)

        for i, m in enumerate(matches, 1):
            match, url = await worker(i, m)
            if not url:
                continue

            logo, cat = build_logo_url(match)
            tv_id = TV_IDS.get(cat, TV_IDS["other"])
            title = strip_non_ascii(match.get("title", "Untitled"))

            content.append(
                f'#EXTINF:-1 tvg-id="{tv_id}" tvg-logo="{logo}" group-title="StreamedSU - {cat.title()}",{title}'
            )
            content.append(url)

        await browser.close()

    return "\n".join(content)


if __name__ == "__main__":
    playlist = asyncio.run(generate_playlist())
    with open("StreamedSU_FILTERED.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)
        if not found:
            html = await page.content()
            m = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^"\'<>]*', html)
            if m:
                found = m[0]

        return found
    except Exception as e:
        total_failures += 1
        log.warning(f"Extract failed: {e}")
        return None


def build_logo(match):
    cat = (match.get("category") or "other").lower()
    logo = FALLBACK.get(cat, FALLBACK["other"])
    return logo, cat


# ============================================================
# PROCESS EACH MATCH
# ============================================================
async def process_match(idx, match, total, ctx):
    global total_embeds, total_streams

    title = strip_ascii(match.get("title"))
    log.info(f"[{idx}/{total}] {title}")

    page = await ctx.new_page()

    for src in match.get("sources", []):
        embeds = get_embed_urls(src)
        total_embeds += len(embeds)

        for eidx, embed in enumerate(embeds, start=1):
            log.info(f"   - ({eidx}/{len(embeds)}) {embed}")
            m3u = await extract_m3u8(page, embed)

            if m3u:
                total_streams += 1
                await page.close()
                return match, m3u

    await page.close()
    return match, None


# ============================================================
# GENERATE PLAYLIST
# ============================================================
async def generate_playlist():
    global total_matches
    matches = fetch_matches()
    total_matches = len(matches)

    if not matches:
        return "#EXTM3U\n"

    output = ["#EXTM3U"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(extra_http_headers=CUSTOM_HEADERS)

        for i, m in enumerate(matches, 1):
            match, url = await process_match(i, m, len(matches), ctx)
            if not url:
                continue

            logo, cat = build_logo(match)
            title = strip_ascii(match.get("title"))
            tv_id = TV_IDS.get(cat, TV_IDS["other"])

            output.append(
                f'#EXTINF:-1 tvg-id="{tv_id}" tvg-name="{title}" tvg-logo="{logo}" '
                f'group-title="StreamedSU - {cat.title()}",{title}'
            )
            output.append(url)

        await browser.close()

    return "\n".join(output)


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    start = datetime.now()
    log.info("🚀 START Scraper Filtered (Football & Basketball)")

    playlist = asyncio.run(generate_playlist())
    with open("StreamedSU_FILTERED.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)

    duration = (datetime.now() - start).total_seconds()
    log.info(f"Finished in {duration:.2f} sec")
