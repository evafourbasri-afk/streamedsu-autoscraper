import asyncio
import re
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# =====================================================
# LOGGING
# =====================================================
logging.basicConfig(
    filename="scrape_fast.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)8s | %(message)s", "%H:%M:%S"))
logging.getLogger("").addHandler(console)
log = logging.getLogger("fast_scraper")


# =====================================================
# CONSTANTS
# =====================================================
CUSTOM_HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

# Only scrape these categories
ALLOWED_CATEGORIES = ["football", "basketball"]

# Default fallback logos
FALLBACK_LOGOS = {
    "football": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/football.png?raw=true",
    "basketball": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/nba.png?raw=true",
    "other": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/default.png?raw=true",
}

TV_IDS = {
    "football": "Soccer.Dummy.us",
    "basketball": "Basketball.Dummy.us",
    "other": "Sports.Dummy.us",
}


# =====================================================
# UTIL
# =====================================================
def strip_non_ascii(text: str) -> str:
    return re.sub(r"[^\x00-\x7F]+", "", text or "")


# =====================================================
# FETCH MATCHES
# =====================================================
def get_all_matches():
    url = "https://streami.su/api/matches/live"
    log.info(f"Fetching {url}")

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        matches = r.json()
        log.info(f"LIVE MATCHES: {len(matches)} total")

        # filter categories
        filtered = [
            m for m in matches
            if (m.get("category") or "").lower().strip() in ALLOWED_CATEGORIES
        ]

        log.info(f"FAST FILTER → {len(filtered)} matches (football+basketball only)")
        return filtered

    except Exception as e:
        log.error(f"Failed to fetch: {e}")
        return []


# =====================================================
# FETCH EMBED LIST
# =====================================================
def get_embed_list(stream_source):
    try:
        src = stream_source.get("source")
        sid = stream_source.get("id")
        url = f"https://streami.su/api/stream/{src}/{sid}"

        r = requests.get(url, timeout=5)
        r.raise_for_status()
        j = r.json()

        return [x.get("embedUrl") for x in j if x.get("embedUrl")]
    except:
        return []


# =====================================================
# M3U8 EXTRACTOR
# =====================================================
async def extract_m3u8(page, embed_url):
    found = None

    try:

        async def on_request(req):
            nonlocal found
            if ".m3u8" in req.url and not found:
                found = req.url
                log.info(f"FOUND STREAM → {found}")

        page.on("request", on_request)

        await page.goto(embed_url, wait_until="domcontentloaded", timeout=6000)

        try:
            await page.mouse.click(200, 200)
        except:
            pass

        for _ in range(12):
            if found:
                break
            await asyncio.sleep(0.25)

        return found

    except Exception as e:
        log.warning(f"extract failed: {e}")
        return None


# =====================================================
# LOGO BUILDER
# =====================================================
def build_logo(match):
    cat = (match.get("category") or "other").lower().strip()

    teams = match.get("teams") or {}
    for side in ["home", "away"]:
        badge = teams.get(side, {}).get("badge")
        if badge:
            badge_url = f"https://streami.su/api/images/badge/{badge}.webp"
            return badge_url, cat

    return FALLBACK_LOGOS.get(cat, FALLBACK_LOGOS["other"]), cat


# =====================================================
# SCRAPE MATCH
# =====================================================
async def scrape_match(idx, match, total, ctx):
    title = strip_non_ascii(match.get("title", "Unknown Match"))
    log.info(f"[{idx}/{total}] {title}")

    page = await ctx.new_page()

    for src in match.get("sources", []):
        embeds = get_embed_list(src)
        if not embeds:
            continue

        for embed in embeds:
            url = await extract_m3u8(page, embed)
            if url:
                await page.close()
                return match, url

    await page.close()
    return match, None


# =====================================================
# GENERATE PLAYLIST
# =====================================================
async def generate_playlist():
    matches = get_all_matches()
    if not matches:
        return "#EXTM3U\n"

    content = ["#EXTM3U"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(extra_http_headers=CUSTOM_HEADERS)

        sem = asyncio.Semaphore(2)

        async def worker(i, m):
            async with sem:
                return await scrape_match(i, m, len(matches), ctx)

        for i, m in enumerate(matches, start=1):
            match, url = await worker(i, m)
            if not url:
                continue

            logo, cat = build_logo(match)
            tv_id = TV_IDS.get(cat, TV_IDS["other"])
            title = strip_non_ascii(match.get("title", "Untitled"))

            content.append(
                f'#EXTINF:-1 tvg-id="{tv_id}" tvg-logo="{logo}" '
                f'group-title="FAST - {cat.title()}",{title}'
            )
            content.append(url)

        await browser.close()

    return "\n".join(content)


# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
    log.info("🚀 FAST MODE STARTED (football + basketball only)")
    start = datetime.now()

    playlist = asyncio.run(generate_playlist())

    with open("StreamedSU_FAST.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)

    log.info("FAST MODE DONE")
