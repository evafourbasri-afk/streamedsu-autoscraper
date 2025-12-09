# ppvsortir_wib.py
import asyncio
from playwright.async_api import async_playwright
import aiohttp
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import time

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
    print(f"ðŸš€  {Col.BOLD}PPV SORTIR LIVE INTERCEPTOR (WIB VERSION){Col.RESET}")
    print(f"{Col.CYAN}{'='*60}{Col.RESET}\n")

API_URL = "https://api.ppv.to/api/streams"
PLAYLIST_FILE = "ppvsortir.m3u"

STREAM_HEADERS = [
    '#EXTVLCOPT:http-referrer=https://ppv.to/',
    '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
]

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

FOOTBALL_MAP = {
    "EPL": ["premier", "epl", "england", "fa cup"],
    "Serie A": ["serie a", "italy"],
    "Bundesliga": ["bundesliga", "germany"],
    "LaLiga": ["laliga", "la liga", "spain"],
    "Ligue 1": ["ligue 1", "france"],
    "UCL": ["champions league", "ucl"],
    "UEL": ["europa league", "uel"],
    "MLS": ["mls"],
    "Libertadores": ["libertadores"]
}

def detect_football_league(name: str):
    n = name.lower()
    for league, keys in FOOTBALL_MAP.items():
        if any(k in n for k in keys):
            return f"Football - {league}"
    return "Football - Other"

# WIB Time Function
def get_display_time(timestamp):
    if not timestamp or timestamp <= 0:
        return ""
    try:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(ZoneInfo("Asia/Jakarta"))
        return dt.strftime("%d %b %Y %H:%M WIB")
    except:
        return ""

async def safe_grab(page, iframe_url, timeout=8):
    try:
        return await asyncio.wait_for(grab_m3u8_from_iframe(page, iframe_url), timeout=timeout)
    except asyncio.TimeoutError:
        return set()

async def grab_m3u8_from_iframe(page, iframe_url):
    first_url = None
    await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image","stylesheet","font","media"] else route.continue_())
    def handle_response(res):
        nonlocal first_url
        if ".m3u8" in res.url and not first_url:
            first_url = res.url
    page.on("response", handle_response)
    try:
        await page.goto(iframe_url, timeout=6000, wait_until="domcontentloaded")
    except:
        pass
    for _ in range(120):
        if first_url:
            break
        await asyncio.sleep(0.05)
    return {first_url} if first_url else set()

async def get_streams():
    try:
        async with aiohttp.ClientSession() as s:
            r = await s.get(API_URL, timeout=30)
            if r.status != 200:
                return []
            return (await r.json()).get("streams", [])
    except:
        return []

async def main():
    print_banner()
    categories = await get_streams()
    if not categories:
        print("âŒ No categories received")
        return

    now = int(time.time())
    flat = []

    for cat in categories:
        cname = cat.get("category","").strip()
        if cname.lower() == "24/7 streams":
            continue

        for s in cat.get("streams", []):
            starts = s.get("starts_at", 0)
            is_live = starts > 0 and starts <= now

            final_cat = cname
            if cname.lower() == "football":
                final_cat = detect_football_league(s.get("name",""))

            cats = [final_cat]
            if is_live:
                cats.append("Live Now")

            if s.get("iframe"):
                flat.append({
                    "id": s["id"],
                    "name": s["name"],
                    "iframe": s["iframe"],
                    "poster": s.get("poster") or BACKUP_LOGOS.get(final_cat.split(" - ")[0], ""),
                    "time": get_display_time(starts),
                    "categories": cats
                })

    flat.sort(key=lambda x: x["name"].lower())
    results = []

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        for s in flat:
            page = await browser.new_page()
            urls = await safe_grab(page, s["iframe"])
            await page.close()
            if urls:
                s["url"] = next(iter(urls))
                results.append(s)
        await browser.close()

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for item in results:
            for cat in item["categories"]:
                group = GROUP_RENAME_MAP.get(cat, cat)
                title = item["name"]
if item["time"]:
    title += f" - {item['time']}"
                f.write(f'#EXTINF:-1 tvg-id="ppv-{item["id"]}" tvg-logo="{item["poster"]}" group-title="{group}",{title}\n')
                for h in STREAM_HEADERS:
                    f.write(h + "\n")
                f.write(item["url"] + "\n")

    print("âœ… Playlist saved:", PLAYLIST_FILE)

if __name__ == "__main__":
    asyncio.run(main())
