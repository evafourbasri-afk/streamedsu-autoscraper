import asyncio
import re
import requests
import logging
from datetime import datetime
from playwright.async_api import async_playwright


# ------------------------------------------------------
# LOGGING SETUP
# ------------------------------------------------------
logging.basicConfig(
    filename="scrape.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)8s | %(message)s", "%H:%M:%S"))
logging.getLogger("").addHandler(console)
log = logging.getLogger("scraper")


# ------------------------------------------------------
# HEADERS & CONSTANTS
# ------------------------------------------------------
CUSTOM_HEADERS = {
    "Origin": "https://embedsports.top",
    "Referer": "https://embedsports.top/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    )
}

# fallback logos by category
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
    "baseball":        "MLB.Baseball.Dummy.us",
    "fight":           "PPV.EVENTS.Dummy.us",
    "american football": "Football.Dummy.us",
    "afl":             "AUS.Rules.Football.Dummy.us",
    "football":        "Soccer.Dummy.us",
    "basketball":      "Basketball.Dummy.us",
    "hockey":          "NHL.Hockey.Dummy.us",
    "tennis":          "Tennis.Dummy.us",
    "darts":           "Darts.Dummy.us",
    "motor sports":    "Racing.Dummy.us",
    "rugby":           "Rugby.Dummy.us",
    "cricket":         "Cricket.Dummy.us",
    "other":           "Sports.Dummy.us"
}

# Global counters
total_matches = 0
total_embeds = 0
total_streams = 0
total_failures = 0


# ------------------------------------------------------
# UTILITY
# ------------------------------------------------------
def strip_non_ascii(text: str) -> str:
    """Remove emojis/non-ASCII characters."""
    if not text:
        return ""
    return re.sub(r"[^\x00-\x7F]+", "", text)


def get_all_matches():
    """Fetch live matches from Streami.su API."""
    endpoints = ["live"]
    all_matches = []

    for ep in endpoints:
        try:
            url = f"https://streami.su/api/matches/{ep}"
            log.info(f"📡 Fetching {url} ...")
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            data = res.json()
            log.info(f"✅ {ep}: {len(data)} matches")
            all_matches.extend(data)
        except Exception as e:
            log.warning(f"⚠️ Failed fetching {ep}: {e}")

    log.info(f"🎯 Total matches collected: {len(all_matches)}")
    return all_matches


def get_embed_list(source):
    """Fetch embedUrl list from Streami.su stream API."""
    try:
        s_name = source.get("source")
        s_id   = source.get("id")
        url = f"https://streami.su/api/stream/{s_name}/{s_id}"
        res = requests.get(url, timeout=6)
        res.raise_for_status()
        data = res.json()
        return [x.get("embedUrl") for x in data if x.get("embedUrl")]
    except:
        return []


# ------------------------------------------------------
# M3U8 Extraction via Playwright
# ------------------------------------------------------
async def extract_m3u8(page, embed_url):
    """Open embedUrl, click through ads, detect .m3u8."""
    global total_failures
    found_url = None

    try:
        # detect requests
        async def on_request(req):
            nonlocal found_url
            if ".m3u8" in req.url and not found_url:
                if "prd.jwpltx.com" in req.url:
                    return
                found_url = req.url
                log.info(f"  ⚡ Stream Found: {found_url}")

        page.on("request", on_request)

        await page.goto(embed_url, wait_until="domcontentloaded", timeout=5000)
        await page.bring_to_front()

        # try clicking any play-related selectors
        selectors = [
            "div.jw-icon-display[role='button']",
            ".jw-icon-playback",
            ".vjs-big-play-button",
            ".plyr__control",
            "div[class*='play']",
            "div[role='button']",
            "button",
            "canvas"
        ]

        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click(timeout=300)
                    break
            except:
                pass

        # attempt click to close ads & start video
        try:
            await page.mouse.click(200, 200)
            pages_before = page.context.pages
            await asyncio.sleep(1)

            # detect new popup
            pages_after = page.context.pages
            if len(pages_after) > len(pages_before):
                new_tab = [p for p in pages_after if p not in pages_before][0]
                try:
                    await new_tab.close()
                except:
                    pass

            await asyncio.sleep(1)
            await page.mouse.click(200, 200)

        except Exception as e:
            log.warning(f"⚠️ Ad click sequence error: {e}")

        # wait briefly
        for _ in range(6):
            if found_url:
                break
            await asyncio.sleep(0.25)

        # fallback: search HTML via regex
        if not found_url:
            html = await page.content()
            m = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^"\'<>]*', html)
            if m:
                found_url = m[0]
                log.info(f"  🕵️ Fallback URL: {found_url}")

        return found_url

    except Exception as e:
        total_failures += 1
        log.warning(f"⚠️ extract_m3u8 failed {embed_url}: {e}")
        return None


# ------------------------------------------------------
# LOGO BUILDER
# ------------------------------------------------------
def validate_logo(url, category):
    try:
        if url:
            r = requests.head(url, timeout=2)
            if r.status_code in (200, 302):
                return url
    except:
        pass

    return FALLBACK_LOGOS.get(category, FALLBACK_LOGOS["other"])


def build_logo(match):
    cat = (match.get("category") or "other").strip().lower()

    teams = match.get("teams") or {}
    for side in ["home", "away"]:
        badge = teams.get(side, {}).get("badge")
        if badge:
            badge_url = f"https://streami.su/api/images/badge/{badge}.webp"
            return validate_logo(badge_url, cat), cat

    # fallback - poster image
    poster = match.get("poster")
    if poster:
        poster_url = f"https://streami.su/api/images/proxy/{poster}.webp"
        return validate_logo(poster_url, cat), cat

    return validate_logo(None, cat), cat


# ------------------------------------------------------
# PROCESS EACH MATCH
# ------------------------------------------------------
async def scrape_match(idx, match, total, ctx):
    global total_embeds, total_streams

    title = strip_non_ascii(match.get("title", "Unknown Match"))
    log.info(f"\n🎯 [{idx}/{total}] Processing: {title}")

    page = await ctx.new_page()
    embed_found = None

    for src in match.get("sources", []):
        embeds = get_embed_list(src)
        total_embeds += len(embeds)

        if not embeds:
            continue

        log.info(f"  ↳ {len(embeds)} embed URLs loaded")

        for i, embed in enumerate(embeds, start=1):
            log.info(f"     • Testing {i}/{len(embeds)}: {embed}")
            m3u8 = await extract_m3u8(page, embed)

            if m3u8:
                total_streams += 1
                embed_found = m3u8
                await page.close()
                return match, embed_found

    await page.close()
    return match, None


# ------------------------------------------------------
# GENERATE PLAYLIST
# ------------------------------------------------------
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

        sem = asyncio.Semaphore(2)

        async def worker(i, m):
            async with sem:
                return await scrape_match(i, m, total_matches, ctx)

        for i, m in enumerate(matches, 1):
            match, url = await worker(i, m)
            if not url:
                continue

            logo, cat = build_logo(match)
            cat_disp = strip_non_ascii(cat.title())
            tv_id = TV_IDS.get(cat, TV_IDS["other"])
            title = strip_non_ascii(match.get("title", "Untitled"))

            content.append(
                f'#EXTINF:-1 tvg-id="{tv_id}" tvg-name="{title}" '
                f'tvg-logo="{logo}" group-title="StreamedSU - {cat_disp}",{title}'
            )
            content.append(f'#EXTVLCOPT:http-origin={CUSTOM_HEADERS["Origin"]}')
            content.append(f'#EXTVLCOPT:http-referrer={CUSTOM_HEADERS["Referer"]}')
            content.append(f'#EXTVLCOPT:user-agent={CUSTOM_HEADERS["User-Agent"]}')
            content.append(url)
            success += 1

        await browser.close()

    log.info(f"\n🎉 {success} working streams written.")
    return "\n".join(content)


# ------------------------------------------------------
# MAIN EXECUTION
# ------------------------------------------------------
if __name__ == "__main__":
    start = datetime.now()

    log.info("🚀 Starting StreamedSU scrape...")
    playlist = asyncio.run(generate_playlist())

    with open("StreamedSU.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)

    duration = (datetime.now() - start).total_seconds()

    # summary
    log.info("\n📊 FINAL SUMMARY")
    log.info(f"Matches:  {total_matches}")
    log.info(f"Embeds:   {total_embeds}")
    log.info(f"Streams:  {total_streams}")
    log.info(f"Failures: {total_failures}")
    log.info(f"Duration: {duration:.2f} sec")
