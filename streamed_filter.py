import asyncio
import re
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# ============================================================
# LOGGING SETUP
# ============================================================
logging.basicConfig(
    filename="scrape_filtered.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%H:%M:%S"))
logging.getLogger("").addHandler(console)
log = logging.getLogger("filtered")

# ============================================================
# SETTINGS
# ============================================================
CUSTOM_HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

ALLOWED_CATEGORIES = {"football", "basketball"}

FALLBACK = {
    "football": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/football.png?raw=true",
    "basketball": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/nba.png?raw=true",
    "other": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/DrewLiveSports.png?raw=true"
}

TV_IDS = {
    "football": "Soccer.Dummy.us",
    "basketball": "Basketball.Dummy.us",
    "other": "Sports.Dummy.us"
}

total_matches = 0
total_embeds = 0
total_streams = 0
total_failures = 0


# ============================================================
# HELPERS
# ============================================================
def strip_ascii(text):
    return re.sub(r"[^\x00-\x7F]+", "", text or "")


def fetch_matches():
    try:
        res = requests.get("https://streami.su/api/matches/live", timeout=10)
        res.raise_for_status()
        data = res.json()
        log.info(f"Total LIVE: {len(data)}")

        filtered = [m for m in data if (m.get("category") or "").lower() in ALLOWED_CATEGORIES]
        log.info(f"Filtered: {len(filtered)} (football + basketball)")
        return filtered
    except Exception as e:
        log.error(f"Failed to fetch matches: {e}")
        return []


def get_embed_urls(src):
    try:
        s, sid = src.get("source"), src.get("id")
        if not s or not sid:
            return []
        res = requests.get(f"https://streami.su/api/stream/{s}/{sid}", timeout=6)
        res.raise_for_status()
        return [x.get("embedUrl") for x in res.json() if x.get("embedUrl")]
    except:
        return []


async def extract_m3u8(page, embed_url):
    global total_failures
    found = None

    async def on_request(req):
        nonlocal found
        if ".m3u8" in req.url and "prd.jwpltx.com" not in req.url:
            found = req.url

    try:
        page.on("request", on_request)
        await page.goto(embed_url, wait_until="domcontentloaded", timeout=6000)

        try:
            await page.mouse.click(200, 200)
        except:
            pass

        for _ in range(12):
            if found:
                break
            await asyncio.sleep(0.3)

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
