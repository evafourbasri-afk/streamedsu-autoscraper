import asyncio
import re
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# ============================================================
# LOGGING
# ============================================================
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

# ============================================================
# CONSTANTS
# ============================================================
CUSTOM_HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# REAL FOOTBALL + BASKETBALL categories used by Streami.su API
ALLOWED_CATEGORIES = [
    # FOOTBALL
    "soccer", "premier league", "laliga", "bundesliga", "serie a",
    "ligue 1", "ucl", "europa league", "international", "efl",
    "mls", "eredivisie", "copa america",

    # BASKETBALL
    "nba", "ncaa", "basketball", "euroleague", "wnba", "nbl"
]

FALLBACK_LOGOS = {
    "football": "https://github.com/BuddyChewChew/My-Streams/raw/main/Logos/sports/football.png",
    "nba": "https://github.com/BuddyChewChew/My-Streams/raw/main/Logos/sports/nba.png",
    "ncaa": "https://github.com/BuddyChewChew/My-Streams/raw/main/Logos/sports/nba.png",
    "soccer": "https://github.com/BuddyChewChew/My-Streams/raw/main/Logos/sports/football.png",
    "basketball": "https://github.com/BuddyChewChew/My-Streams/raw/main/Logos/sports/nba.png",
    "other": "https://github.com/BuddyChewChew/My-Streams/raw/main/Logos/sports/DrewLiveSports.png",
}

TV_IDS = {
    "soccer": "Soccer.Dummy.id",
    "premier league": "Premier.Dummy.id",
    "laliga": "LaLiga.Dummy.id",
    "bundesliga": "Bundesliga.Dummy.id",
    "serie a": "SerieA.Dummy.id",
    "nba": "NBA.Dummy.us",
    "ncaa": "NCAA.Dummy.us",
    "basketball": "Basketball.Dummy.us",
    "euroleague": "Euroleague.Dummy.us",
}

total_matches = 0
total_embeds = 0
total_streams = 0
total_failures = 0

# ============================================================
# UTIL
# ============================================================
def strip(text):
    return re.sub(r"[^\x00-\x7F]+", "", text or "")

def get_matches():
    log.info("📡 Fetching live matches...")
    try:
        res = requests.get("https://streami.su/api/matches/live", timeout=10)
        res.raise_for_status()
        all_data = res.json()
    except:
        log.error("❌ Cannot fetch API")
        return []

    filtered = []
    for m in all_data:
        cat = (m.get("category") or "").lower().strip()
        if cat in ALLOWED_CATEGORIES:
            filtered.append(m)

    log.info(f"🎯 Filter matched events: {len(filtered)}")
    return filtered

def get_embed_list(src):
    try:
        name, sid = src.get("source"), src.get("id")
        url = f"https://streami.su/api/stream/{name}/{sid}"
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        data = r.json()
        return [d.get("embedUrl") for d in data if d.get("embedUrl")]
    except:
        return []

async def get_m3u8(page, embed):
    global total_failures
    found = None
    try:
        async def on_req(req):
            nonlocal found
            if ".m3u8" in req.url and "jwpltx" not in req.url:
                found = req.url

        page.on("request", on_req)
        await page.goto(embed, wait_until="domcontentloaded", timeout=7000)

        await page.mouse.click(200, 200)
        await asyncio.sleep(1)

        return found
    except:
        total_failures += 1
        return None

def pick_logo(match):
    cat = (match.get("category") or "").lower()
    return FALLBACK_LOGOS.get(cat, FALLBACK_LOGOS["other"])

# ============================================================
# PROCESS MATCH
# ============================================================
async def process_match(i, match, total, ctx):
    global total_embeds, total_streams
    title = strip(match.get("title"))
    log.info(f"\n⚽ [{i}/{total}] {title}")

    page = await ctx.new_page()

    for src in match.get("sources", []):
        embeds = get_embed_list(src)
        total_embeds += len(embeds)

        for emb in embeds:
            log.info(f"  → Testing {emb}")
            m3u8 = await get_m3u8(page, emb)
            if m3u8:
                total_streams += 1
                await page.close()
                return match, m3u8

    await page.close()
    return match, None

# ============================================================
# PLAYLIST BUILDER
# ============================================================
async def build_playlist():
    matches = get_matches()
    if not matches:
        return "#EXTM3U\n"

    out = ["#EXTM3U"]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(extra_http_headers=CUSTOM_HEADERS)

        for i, m in enumerate(matches, 1):
            match, url = await process_match(i, m, len(matches), ctx)
            if not url:
                continue

            title = strip(match.get("title"))
            cat = (match.get("category") or "other").lower().strip()

            logo = pick_logo(match)
            tv_id = TV_IDS.get(cat, "Sports.Dummy.id")

            out.append(f'#EXTINF:-1 tvg-id="{tv_id}" tvg-logo="{logo}" group-title="{cat.title()}",{title}')
            out.append(url)

        await browser.close()

    return "\n".join(out)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    start = datetime.now()
    log.info("🚀 Starting StreamedSU FILTERED scraper...")

    playlist = asyncio.run(build_playlist())

    with open("StreamedSU_FILTERED.m3u8", "w") as f:
        f.write(playlist)

    log.info("✅ DONE")        async def on_request(request):
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
