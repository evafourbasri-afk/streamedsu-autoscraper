import asyncio
import re
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# ================= LOGGING =================
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

# ================= CONSTANTS =================
CUSTOM_HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": "Mozilla/5.0"
}

ALLOWED = ["football", "basketball"]

total_matches = 0
total_embeds = 0
total_streams = 0
total_failures = 0


# ================= HELPERS =================
def strip_non_ascii(text):
    return re.sub(r"[^\x00-\x7F]+", "", text or "")


def get_matches():
    try:
        res = requests.get("https://streami.su/api/matches/live", timeout=15)
        res.raise_for_status()
        data = res.json()
        filtered = []

        for m in data:
            cat = (m.get("category") or "").lower()
            if any(x in cat for x in ALLOWED):
                filtered.append(m)

        log.info(f"Total filtered matches: {len(filtered)}")
        return filtered

    except Exception as e:
        log.error(f"Error fetching matches: {e}")
        return []


def get_embed_list(src):
    try:
        api = f"https://streami.su/api/stream/{src['source']}/{src['id']}"
        r = requests.get(api, timeout=10)
        r.raise_for_status()
        return [x.get("embedUrl") for x in r.json() if x.get("embedUrl")]
    except:
        return []


# ============ PLAYWRIGHT CORE ===============
async def extract_m3u8(page, embed_url):
    found = None

    try:
        async def on_request(req):
            nonlocal found
            if ".m3u8" in req.url and "jwpltx" not in req.url:
                found = req.url
                log.info(f"FOUND M3U8: {found}")

        page.on("request", on_request)

        await page.goto(embed_url, wait_until="domcontentloaded", timeout=8000)

        # Try clicking to start player
        try:
            await page.mouse.click(200, 200)
        except:
            pass

        await asyncio.sleep(1.2)

        if found:
            return found

        # fallback scan HTML
        html = await page.content()
        m = re.findall(r'https?://[^\s"<]+\.m3u8[^\s"<]*', html)
        if m:
            return m[0]

        return None

    except Exception as e:
        log.warning(f"extract error: {e}")
        return None


# ============ PROCESS MATCH =============
async def process_match(i, match, total, ctx):
    title = strip_non_ascii(match.get("title"))
    cat = match.get("category", "").lower()

    log.info(f"[{i}/{total}] {title} ({cat})")

    page = await ctx.new_page()

    for src in match.get("sources", []):
        embeds = get_embed_list(src)
        if not embeds:
            continue

        log.info(f"Embed count: {len(embeds)}")

        for embed in embeds:
            m3u8 = await extract_m3u8(page, embed)
            if m3u8:
                await page.close()
                return match, m3u8

    await page.close()
    return match, None


# ============ GENERATE PLAYLIST ============
async def generate_playlist():
    matches = get_matches()
    if not matches:
        return "#EXTM3U\n"

    out = ["#EXTM3U"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome-beta")
        ctx = await browser.new_context(extra_http_headers=CUSTOM_HEADERS)

        for i, m in enumerate(matches, start=1):
            match, url = await process_match(i, m, len(matches), ctx)
            if not url:
                continue

            title = strip_non_ascii(match.get("title"))
            cat = match.get("category", "").title()

            out.append(f'#EXTINF:-1 group-title="{cat}",{title}')
            out.append(url)

        await browser.close()

    return "\n".join(out)


# ============ MAIN ============
if __name__ == "__main__":
    log.info("Starting FULL Filtered Scraper...")

    playlist = asyncio.run(generate_playlist())

    with open("StreamedSU_FILTERED.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)

    log.info("DONE → StreamedSU_FILTERED.m3u8 created.")
