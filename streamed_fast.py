import asyncio
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("FAST")

API_URL = "https://streami.su/api/matches/live"

FAST_CATEGORIES = ["football", "basketball"]

CUSTOM_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://embedsports.top/",
    "Origin": "https://embedsports.top",
}


async def extract_stream(page, embed_url):
    found = None

    def on_request(req):
        nonlocal found
        if ".m3u8" in req.url and "prd.jwpltx.com" not in req.url:
            found = req.url
            log.info(f"⚡ Found stream: {found}")

    page.on("request", on_request)

    try:
        await page.goto(embed_url, wait_until="domcontentloaded", timeout=7000)
        await page.mouse.click(200, 200)
        await asyncio.sleep(2)
    except:
        return None

    return found


async def process_match(ctx, match, index, total):
    title = match.get("title", "Unknown")
    category = (match.get("category") or "").lower()

    log.info(f"[{index}/{total}] 🎯 {title}  ({category})")

    sources = match.get("sources", [])
    page = await ctx.new_page()

    for src in sources:
        sname = src.get("source")
        sid = src.get("id")
        if not sname or not sid:
            continue

        try:
            r = requests.get(f"https://streami.su/api/stream/{sname}/{sid}", timeout=5)
            r.raise_for_status()
            embeds = [d.get("embedUrl") for d in r.json() if d.get("embedUrl")]
        except:
            continue

        for url in embeds:
            log.info(f"   → Try embed: {url}")
            m3u8 = await extract_stream(page, url)
            if m3u8:
                await page.close()
                return m3u8

    await page.close()
    return None


async def main():
    start = datetime.now()

    log.info("FAST MODE STARTED (football + basketball)")

    try:
        data = requests.get(API_URL, timeout=10).json()
    except:
        log.error("Failed to fetch match list")
        return

    matches = [
        m for m in data
        if m.get("category", "").lower() in FAST_CATEGORIES
    ]

    log.info(f"FAST FILTER → {len(matches)} matches")

    out = ["#EXTM3U"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(extra_http_headers=CUSTOM_HEADERS)

        for i, match in enumerate(matches, 1):
            stream = await process_match(ctx, match, i, len(matches))
            if not stream:
                continue

            title = match.get("title", "Unknown")
            out.append(f'#EXTINF:-1 group-title="FAST", {title}')
            out.append(stream)

        await browser.close()

    with open("StreamedSU_FAST.m3u8", "w") as f:
        f.write("\n".join(out))

    log.info("FAST MODE DONE")
    log.info(f"Saved: StreamedSU_FAST.m3u8")


if __name__ == "__main__":
    asyncio.run(main())
