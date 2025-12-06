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
    level=logging.INFO,
    format="%(asctime)s | %(levelname)8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("FAST")

HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

ALLOWED = ["football", "basketball"]

# ============================================================
# FETCH MATCHES
# ============================================================
def get_matches():
    url = "https://streami.su/api/matches/live"
    log.info(f"Fetching {url}")
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        log.info(f"LIVE MATCHES: {len(data)} total")
        return data
    except Exception as e:
        log.error(f"Failed loading live matches: {e}")
        return []


# ============================================================
# AGGRESSIVE M3U8 EXTRACTOR (from streamed.py)
# ============================================================
async def extract_m3u8(page, embed_url):
    found = None

    async def on_request(req):
        nonlocal found
        if ".m3u8" in req.url and not found:
            if "prd.jwpltx.com" in req.url:
                return
            found = req.url
            log.info(f"⚡ Stream Found: {found}")

    page.on("request", on_request)

    try:
        await page.goto(embed_url, wait_until="domcontentloaded", timeout=8000)
        await asyncio.sleep(1)

        # Aggressive clicker
        selectors = [
            "div.jw-icon-display",
            "button",
            ".vjs-big-play-button",
            "[role='button']",
            "canvas"
        ]

        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    await asyncio.sleep(0.5)
            except:
                pass

        # Try random clicks for ads
        try:
            await page.mouse.click(200, 200)
            await asyncio.sleep(0.8)
            await page.mouse.click(300, 250)
            await asyncio.sleep(0.8)
        except:
            pass

        # Wait max 8 seconds for stream detection
        for _ in range(16):
            if found:
                break
            await asyncio.sleep(0.5)

        # Regex fallback
        if not found:
            html = await page.content()
            m = re.findall(r'https?://[^"\']+\.m3u8[^"\']*', html)
            if m:
                found = m[0]
                log.info(f"🕵️ Regex fallback → {found}")

    except Exception as e:
        log.warning(f"extract_m3u8 error: {e}")

    return found


# ============================================================
# PROCESS MATCH
# ============================================================
async def process_match(i, match, ctx, total):
    cat = (match.get("category") or "").lower()
    title = re.sub(r"[^\x00-\x7F]+", "", match.get("title", "Unknown"))

    log.info(f"[{i}/{total}] {title}")

    embed_urls = []
    for src in match.get("sources", []):
        try:
            res = requests.get(
                f"https://streami.su/api/stream/{src['source']}/{src['id']}",
                timeout=6
            )
            res.raise_for_status()
            data = res.json()
            embed_urls.extend([x.get("embedUrl") for x in data if x.get("embedUrl")])
        except:
            pass

    if not embed_urls:
        return None, None, None

    page = await ctx.new_page()

    for emb in embed_urls:
        log.info(f" → Testing: {emb}")
        m3u8 = await extract_m3u8(page, emb)
        if m3u8:
            await page.close()
            return m3u8, title, cat

    await page.close()
    return None, None, None


# ============================================================
# MAIN
# ============================================================
async def main():
    matches = get_matches()
    filtered = [m for m in matches if (m.get("category") or "").lower() in ALLOWED]

    log.info(f"FAST FILTER → {len(filtered)} matches (football+basketball only)")

    playlist = ["#EXTM3U"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(extra_http_headers=HEADERS)

        for i, m in enumerate(filtered, 1):
            m3u8, title, cat = await process_match(i, m, ctx, len(filtered))

            if not m3u8:
                continue

            playlist.append(
                f'#EXTINF:-1 group-title="FAST-{cat.title()}",{title}'
            )
            playlist.append(m3u8)

        await browser.close()

    log.info("FAST MODE DONE")
    return "\n".join(playlist)


if __name__ == "__main__":
    start = datetime.now()
    text = asyncio.run(main())

    with open("StreamedSU_FAST.m3u8", "w", encoding="utf-8") as f:
        f.write(text)

    log.info("Saved → StreamedSU_FAST.m3u8")    found = None

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
