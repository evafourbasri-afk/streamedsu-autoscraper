import asyncio
import re
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# ==========================
# LOGGING
# ==========================
logging.basicConfig(
    filename="scrape_filter.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%H:%M:%S"))
logging.getLogger("").addHandler(console)
log = logging.getLogger("filter")

# ==========================
# CONSTANTS
# ==========================
CUSTOM_HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

ALLOWED_CATEGORIES = ["football", "basketball"]

FALLBACK_LOGOS = {
    "football": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/football.png?raw=true",
    "basketball": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/nba.png?raw=true",
    "other": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/DrewLiveSports.png?raw=true",
}

TV_IDS = {
    "football": "Soccer.Dummy.us",
    "basketball": "Basketball.Dummy.us",
    "other": "Sports.Dummy.us",
}

total_matches = total_embeds = total_streams = total_failures = 0


# ==========================
# HELPERS
# ==========================
def strip_non_ascii(text):
    return re.sub(r"[^\x00-\x7F]+", "", text or "")


def get_all_matches():
    try:
        res = requests.get("https://streami.su/api/matches/live", timeout=10)
        res.raise_for_status()
        data = res.json()
        log.info(f"Fetched {len(data)} live matches.")

        # FILTER CATEGORY HERE
        filtered = []
        for m in data:
            cat = (m.get("category") or "").lower()
            if any(key in cat for key in ALLOWED_CATEGORIES):
                filtered.append(m)

        log.info(f"Filtered: {len(filtered)} (football + basketball).")
        return filtered

    except Exception as e:
        log.error(f"Failed fetching live matches: {e}")
        return []


def get_embed_urls(src):
    try:
        api = f"https://streami.su/api/stream/{src.get('source')}/{src.get('id')}"
        res = requests.get(api, timeout=6)
        if res.status_code != 200:
            return []
        return [x.get("embedUrl") for x in res.json() if x.get("embedUrl")]
    except:
        return []


async def extract_m3u8(page, embed_url):
    found = None

    try:
        async def on_request(req):
            nonlocal found
            if ".m3u8" in req.url:
                if "prd.jwpltx.com" not in req.url:
                    found = req.url

        page.on("request", on_request)

        await page.goto(embed_url, timeout=7000, wait_until="domcontentloaded")

        # Click to bypass ads
        try:
            await page.mouse.click(200, 200)
        except:
            pass

        await asyncio.sleep(1.2)

        if found:
            return found

        # fallback: search HTML
        html = await page.content()
        matches = re.findall(r'https?://[^\s"<]+\.m3u8[^\s"<]*', html)
        if matches:
            return matches[0]

        return None

    except Exception as e:
        log.warning(f"extract failed: {e}")
        return None


def pick_logo(cat):
    cat = cat.lower()
    if "football" in cat:
        return FALLBACK_LOGOS["football"]
    elif "basketball" in cat:
        return FALLBACK_LOGOS["basketball"]
    return FALLBACK_LOGOS["other"]


# ==========================
# MAIN PROCESS MATCH
# ==========================
async def process_match(i, match, total, ctx):
    title = strip_non_ascii(match.get("title"))
    category = (match.get("category") or "").lower()

    log.info(f"[{i}/{total}] {title} ({category})")

    page = await ctx.new_page()

    for src in match.get("sources", []):
        embeds = get_embed_urls(src)

        for embed in embeds:
            m3u8 = await extract_m3u8(page, embed)
            if m3u8:
                await page.close()
                return match, m3u8

    await page.close()
    return match, None


# ==========================
# GENERATE PLAYLIST
# ==========================
async def generate_playlist():
    matches = get_all_matches()
    if not matches:
        return "#EXTM3U\n"

    output = ["#EXTM3U"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(extra_http_headers=CUSTOM_HEADERS)

        for i, m in enumerate(matches, start=1):
            match, url = await process_match(i, m, len(matches), ctx)
            if not url:
                continue

            cat = (match.get("category") or "").lower()
            title = strip_non_ascii(match.get("title"))
            logo = pick_logo(cat)
            tvg = TV_IDS.get(cat, TV_IDS["other"])

            output.append(f'#EXTINF:-1 tvg-id="{tvg}" tvg-logo="{logo}" group-title="{cat.title()}",{title}')
            output.append(url)

        await browser.close()

    return "\n".join(output)


# ==========================
# ENTRY POINT
# ==========================
if __name__ == "__main__":
    log.info("Starting filtered scraper (football + basketball)...")

    playlist = asyncio.run(generate_playlist())

    with open("StreamedSU_FILTERED.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)

    log.info("DONE.")
