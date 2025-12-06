import asyncio
import re
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# ------------------------------------------------------
# LOGGING
# ------------------------------------------------------
logging.basicConfig(
    filename="scrape_fast.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%H:%M:%S"))
logging.getLogger("").addHandler(console)
log = logging.getLogger("FAST")

# ------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------
CUSTOM_HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

FALLBACK_LOGOS = {
    "american football": "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/nfl.png?raw=true",
    "football":          "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/football.png?raw=true",
    "fight":             "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/mma.png?raw=true",
    "basketball":        "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/nba.png?raw=true",
    "motor sports":      "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/f1.png?raw=true",
    "darts":             "https://github.com/BuddyChewChew/My-Streams/blob/main/Logos/sports/darts2.png?raw=true",
    "tennis":            "http://drewlive24.duckdns.org:9000/Logos/Tennis-2.png",
    "rugby":             "http://drewlive24.duckdns.org:9000/Logos/Rugby.png",
    "cricket":           "http://drewlive24.duckdns.org:9000/Logos/Cricket.png",
    "golf":              "http://drewlive24.duckdns.org:9000/Logos/Golf.png",
    "other":             "http://drewlive24.duckdns.org:9000/Logos/DrewLiveSports.png"
}

TV_IDS = {
    "baseball": "MLB.Baseball.Dummy.us",
    "fight": "PPV.EVENTS.Dummy.us",
    "american football": "Football.Dummy.us",
    "afl": "AUS.Rules.Football.Dummy.us",
    "football": "Soccer.Dummy.us",
    "basketball": "Basketball.Dummy.us",
    "hockey": "NHL.Hockey.Dummy.us",
    "tennis": "Tennis.Dummy.us",
    "darts": "Darts.Dummy.us",
    "motor sports": "Racing.Dummy.us",
    "rugby": "Rugby.Dummy.us",
    "cricket": "Cricket.Dummy.us",
    "other": "Sports.Dummy.us"
}

total_matches = 0
total_embeds = 0
total_streams = 0
total_failures = 0


# ------------------------------------------------------
# HELPERS
# ------------------------------------------------------
def strip_non_ascii(text: str) -> str:
    return re.sub(r"[^\x00-\x7F]+", "", text or "")


def get_all_matches():
    try:
        log.info("Fetching live matches...")
        res = requests.get("https://streami.su/api/matches/live", timeout=10)
        data = res.json()
        log.info(f"Live matches: {len(data)} found")
        return data
    except:
        return []


def get_embed_urls(source):
    try:
        sid = source.get("id")
        src = source.get("source")
        if not sid or not src:
            return []
        url = f"https://streami.su/api/stream/{src}/{sid}"
        r = requests.get(url, timeout=6).json()
        return [x.get("embedUrl") for x in r if x.get("embedUrl")]
    except:
        return []


# ------------------------------------------------------
# EXTRACT M3U8
# ------------------------------------------------------
async def extract_m3u8(page, embed_url):
    global total_failures
    found = None

    try:
        async def on_req(req):
            nonlocal found
            if ".m3u8" in req.url and "prd.jwpltx.com" not in req.url:
                found = req.url
                log.info(f"  ⚡ Stream Found: {found}")

        page.on("request", on_req)

        await page.goto(embed_url, wait_until="domcontentloaded", timeout=5000)

        # try click players
        selectors = [
            "div.jw-icon-display", ".jw-icon-playback",
            ".vjs-big-play-button", "button", "canvas"
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    break
            except:
                pass

        # anti-ad click
        try:
            await page.mouse.click(200, 200)
            await asyncio.sleep(1)
            # close popup if appeared
            for p in page.context.pages:
                if p != page:
                    try:
                        await p.close()
                    except:
                        pass
        except:
            pass

        for _ in range(8):
            if found:
                break
            await asyncio.sleep(0.3)

        if not found:
            html = await page.content()
            m = re.findall(r'https?://[^\s"<]+\.m3u8[^\s"<]*', html)
            if m:
                found = m[0]
                log.info(f"  🕵️ Fallback: {found}")

        return found

    except Exception as e:
        total_failures += 1
        log.warning(f"extract failed: {e}")
        return None


# ------------------------------------------------------
# LOGO BUILDER
# ------------------------------------------------------
def build_logo(match):
    cat = (match.get("category") or "other").lower()
    teams = match.get("teams") or {}

    for s in ["home", "away"]:
        badge = teams.get(s, {}).get("badge")
        if badge:
            url = f"https://streami.su/api/images/badge/{badge}.webp"
            try:
                if requests.head(url, timeout=2).status_code in (200, 302):
                    return url, cat
            except:
                pass

    poster = match.get("poster")
    if poster:
        url = f"https://streami.su/api/images/proxy/{poster}.webp"
        try:
            if requests.head(url, timeout=2).status_code in (200, 302):
                return url, cat
        except:
            pass

    return FALLBACK_LOGOS.get(cat, FALLBACK_LOGOS["other"]), cat


# ------------------------------------------------------
# PROCESS MATCH
# ------------------------------------------------------
async def process_match(i, match, total, ctx):
    global total_embeds, total_streams

    title = strip_non_ascii(match.get("title"))
    log.info(f"[{i}/{total}] {title}")

    page = await ctx.new_page()

    for s in match.get("sources", []):
        embeds = get_embed_urls(s)
        total_embeds += len(embeds)

        for idx, embed in enumerate(embeds, 1):
            log.info(f"   • ({idx}/{len(embeds)}) {embed}")
            m3u8 = await extract_m3u8(page, embed)
            if m3u8:
                total_streams += 1
                await page.close()
                return match, m3u8

    await page.close()
    return match, None


# ------------------------------------------------------
# GENERATE FAST PLAYLIST (ONLY football + basketball)
# ------------------------------------------------------
async def generate_playlist():
    global total_matches

    matches = get_all_matches()
    total_matches = len(matches)

    # FILTER ONLY FOOTBALL + BASKETBALL
    ALLOWED = ["football", "basketball"]
    matches = [m for m in matches if (m.get("category") or "").lower() in ALLOWED]
    log.info(f"FAST FILTER → {len(matches)} matches kept (football + basketball)")

    if not matches:
        return "#EXTM3U\n"

    content = ["#EXTM3U"]
    success = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome-beta")
        ctx = await browser.new_context(extra_http_headers=CUSTOM_HEADERS)

        sem = asyncio.Semaphore(2)

        async def worker(i, m):
            async with sem:
                return await process_match(i, m, len(matches), ctx)

        for i, m in enumerate(matches, 1):
            match, url = await worker(i, m)
            if not url:
                continue

            logo, cat = build_logo(match)
            cat_disp = strip_non_ascii(cat.title())
            title = strip_non_ascii(match.get("title"))
            tv_id = TV_IDS.get(cat, TV_IDS["other"])

            content.append(
                f'#EXTINF:-1 tvg-id="{tv_id}" tvg-logo="{logo}" '
                f'group-title="FAST - {cat_disp}",{title}'
            )
            content.append(url)
            success += 1

        await browser.close()

    log.info(f"FAST DONE → {success} streams OK")
    return "\n".join(content)


# ------------------------------------------------------
# MAIN
# ------------------------------------------------------
if __name__ == "__main__":
    log.info("🚀 FAST SCRAPER STARTED (football + basketball)")
    start = datetime.now()

    playlist = asyncio.run(generate_playlist())
    with open("StreamedSU_FAST.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)

    dur = (datetime.now() - start).total_seconds()
    log.info(f"⏱ Duration: {dur:.2f}s")
    log.info("DONE.")        res.raise_for_status()
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
