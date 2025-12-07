import asyncio
from playwright.async_api import async_playwright
import aiohttp
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import time

# --- 🎨 VISUALS ---
class Col:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def print_banner():
    print(f"\n{Col.CYAN}{'='*60}{Col.RESET}")
    print(f"🚀  {Col.BOLD}PPV.TO LIVE INTERCEPTOR - MASTER PLAYLIST FIX{Col.RESET}")
    print(f"{Col.CYAN}{'='*60}{Col.RESET}\n")


# --- CONFIG ---
API_URL = "https://api.ppv.to/api/streams"
PLAYLIST_FILE = "ppvreal.m3u"

STREAM_HEADERS = [
    '#EXTVLCOPT:http-referrer=https://ppv.to/',
    '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
]


# --- BACKUP LOGO ---
BACKUP_LOGOS = {
    "Wrestling": "http://drewlive2423.duckdns.org:9000/Logos/Wrestling.png",
    "Football": "http://drewlive2423.duckdns.org:9000/Logos/Football.png",
    "Basketball": "http://drewlive2423.duckdns.org:9000/Logos/Basketball.png",
    "Baseball": "http://drewlive2423.duckdns.org:9000/Logos/Baseball.png",
    "American Football": "http://drewlive2423.duckdns.org:9000/Logos/NFL3.png",
    "Combat Sports": "http://drewlive2423.duckdns.org:9000/Logos/CombatSports2.png",
    "Darts": "http://drewlive2423.duckdns.org:9000/Logos/Darts.png",
    "Motorsports": "http://drewlive2423.duckdns.org:9000/Logos/Motorsports2.png",
    "Live Now": "http://drewlive2423.duckdns.org:9000/Logos/DrewLiveSports.png",
    "Ice Hockey": "http://drewlive2423.duckdns.org:9000/Logos/Hockey.png",
    "Cricket": "http://drewlive2423.duckdns.org:9000/Logos/Cricket.png",
}


# --- GROUP RENAME ---
GROUP_RENAME_MAP = {
    "Wrestling": "PPVLand - Wrestling Events",
    "Football": "PPVLand - Global Football Streams",
    "Basketball": "PPVLand - Basketball Hub",
    "Baseball": "PPVLand - MLB",
    "American Football": "PPVLand - NFL Action",
    "Combat Sports": "PPVLand - Combat Sports",
    "Darts": "PPVLand - Darts",
    "Motorsports": "PPVLand - Racing Action",
    "Live Now": "PPVLand - Live Now",
    "Ice Hockey": "PPVLand - NHL Action",
    "Cricket": "PPVLand - Cricket"
}

ICONS = {
    "American Football": "🏈", "Basketball": "🏀", "Ice Hockey": "🏒",
    "Baseball": "⚾", "Combat Sports": "🥊", "Wrestling": "🤼",
    "Football": "⚽", "Motorsports": "🏎️", "Darts": "🎯",
    "Live Now": "📡", "default": "📺"
}


def get_icon(name):
    return ICONS.get(name, ICONS["default"])


def get_display_time(timestamp):
    if not timestamp or timestamp <= 0:
        return ""
    try:
        dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        dt_est = dt_utc.astimezone(ZoneInfo("America/New_York"))
        dt_mt = dt_utc.astimezone(ZoneInfo("America/Denver"))
        dt_uk = dt_utc.astimezone(ZoneInfo("Europe/London"))
        return f"{dt_est.strftime('%I:%M %p ET')} / {dt_mt.strftime('%I:%M %p MT')} / {dt_uk.strftime('%H:%M UK')}"
    except:
        return ""


# --- NEW: MASTER PLAYLIST FIX ---
def convert_to_master(url: str) -> str:
    """
    Jika URL adalah child playlist seperti:
    .../tracks-v1a1/mono.ts.m3u8

    Maka otomatis diganti menjadi master playlist:
    .../index.m3u8
    """
    if "tracks" in url:
        parts = url.split("/")
        return "/".join(parts[:-2]) + "/index.m3u8"
    return url


# --- SCRAPING FUNCTION (FIXED) ---
async def grab_m3u8_from_iframe(page, iframe_url):
    first_url = None

    # Block unneeded resources
    await page.route("**/*", lambda route: (
        route.abort() if route.request.resource_type in ["image", "stylesheet", "font"] else route.continue_()
    ))

    def handle_response(response):
        nonlocal first_url
        url = response.url

        if ".m3u8" in url and first_url is None:
            fixed = convert_to_master(url)
            first_url = fixed

    page.on("response", handle_response)

    try:
        await page.goto(iframe_url, timeout=8000, wait_until="domcontentloaded")
    except:
        pass

    # Wait until URL captured
    for _ in range(150):
        if first_url:
            break
        await asyncio.sleep(0.05)

    return {first_url} if first_url else set()


# --- SAFE WRAPPER ---
async def safe_grab(page, url):
    try:
        return await asyncio.wait_for(grab_m3u8_from_iframe(page, url), timeout=10)
    except asyncio.TimeoutError:
        return set()


# --- API FETCH ---
async def get_streams():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            resp = await session.get(API_URL, timeout=20)
            if resp.status != 200:
                print(f"{Col.RED}❌ API Error {resp.status}{Col.RESET}")
                return []
            data = await resp.json()
            return data.get("streams", [])
    except:
        return []


# --- MAIN PROCESS ---
async def main():
    print_banner()
    start = time.time()

    categories = await get_streams()
    if not categories:
        print(f"{Col.RED}❌ API returned no data!{Col.RESET}")
        return

    now_ts = int(time.time())
    streams = []

    # Flatten + remove 24/7
    for cat in categories:
        original = cat["category"]

        if original.lower() == "24/7 streams":
            continue

        cat_always_live = cat.get("always_live") == 1

        for s in cat.get("streams", []):
            starts_at = s.get("starts_at", 0)
            live_event = starts_at <= now_ts and starts_at > 0
            stream_always_live = s.get("always_live") == 1

            final_cat = original
            if live_event and not cat_always_live:
                final_cat = "Live Now"

            if s.get("iframe"):
                streams.append({
                    "id": s["id"],
                    "name": s["name"],
                    "iframe": s["iframe"],
                    "poster": s.get("poster"),
                    "category": final_cat,
                    "starts_at": starts_at,
                    "time": get_display_time(starts_at)
                })

    streams.sort(key=lambda x: x["starts_at"])
    valid = []

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)

        for idx, s in enumerate(streams, 1):
            page = await browser.new_page()
            icon = get_icon(s["category"])
            print(f"[{idx}/{len(streams)}] {icon} {s['name']} ...")

            urls = await safe_grab(page, s["iframe"])
            await page.close()

            if urls:
                url = list(urls)[0]
                print(f"   {Col.GREEN}✔ Master Playlist:{Col.RESET} {url}")

                poster = s["poster"] or BACKUP_LOGOS.get(s["category"], "")

                valid.append({
                    "id": s["id"],
                    "name": s["name"],
                    "category": s["category"],
                    "poster": poster,
                    "url": url,
                    "time": s["time"]
                })
            else:
                print(f"   {Col.RED}✘ No m3u8 found{Col.RESET}")

        await browser.close()

    # SAVE M3U OUTPUT
    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for v in valid:
            group = GROUP_RENAME_MAP.get(v["category"], v["category"])
            clean_title = v["name"]

            if v["time"]:
                clean_title += f" - {v['time']}"

            f.write(f'#EXTINF:-1 tvg-id="ppv-{v["id"]}" tvg-logo="{v["poster"]}" group-title="{group}",{clean_title}\n')
            for h in STREAM_HEADERS:
                f.write(h + "\n")
            f.write(v["url"] + "\n")

    print(f"\n{Col.CYAN}==========================================={Col.RESET}")
    print(f"✅ DONE! Saved playlist: {PLAYLIST_FILE}")
    print(f"📌 Total Working Streams: {len(valid)}")
    print(f"⏱ Time: {time.time() - start:.1f}s")
    print(f"{Col.CYAN}==========================================={Col.RESET}")


if __name__ == "__main__":
    asyncio.run(main())
