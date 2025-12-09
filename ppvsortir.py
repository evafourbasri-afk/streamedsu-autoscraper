# ppvsortir_wib.py
# VERSION: WIB + SORTING + FOOTBALL SUBCATEGORY + NO RESTREAM
import asyncio
from playwright.async_api import async_playwright
import aiohttp
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import time

API_URL = "https://api.ppv.to/api/streams"
PLAYLIST_FILE = "ppvgit.m3u"

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
    "EPL": ["premier", "epl", "england"],
    "Serie A": ["serie a", "italy"],
    "Bundesliga": ["bundesliga", "germany"],
    "LaLiga": ["laliga", "la liga", "spain"],
    "Ligue 1": ["ligue 1"],
    "UCL": ["champions league", "ucl"],
    "UEL": ["europa league", "uel"],
    "MLS": ["mls"],
    "Libertadores": ["libertadores"]
}

def detect_football(name):
    n = name.lower()
    for league, keys in FOOTBALL_MAP.items():
        if any(k in n for k in keys):
            return f"Football - {league}"
    return "Football - Other"

def get_time_wib(ts):
    if not ts or ts <= 0:
        return ""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(ZoneInfo("Asia/Jakarta"))
    return dt.strftime("%d %b %Y %H:%M WIB")

async def safe_grab(page, url):
    try:
        return await asyncio.wait_for(grab(page, url), timeout=8)
    except:
        return set()

async def grab(page, url):
    first = None
    await page.route("**/*", lambda r: r.abort() if r.request.resource_type in ["image","font","stylesheet","media"] else r.continue_())

    def on_res(res):
        nonlocal first
        if ".m3u8" in res.url and not first:
            first = res.url

    page.on("response", on_res)

    try:
        await page.goto(url, timeout=6000)
    except:
        pass

    for _ in range(150):
        if first:
            break
        await asyncio.sleep(0.05)

    return {first} if first else set()

async def get_streams():
    try:
        async with aiohttp.ClientSession() as s:
            r = await s.get(API_URL, timeout=20)
            return (await r.json()).get("streams", [])
    except:
        return []

async def main():
    data = await get_streams()
    if not data:
        print("NO STREAM DATA")
        return

    now = int(time.time())
    flat = []

    for cat in data:
        cname = cat.get("category","").strip()
        if cname.lower() == "24/7 streams":
            continue

        for s in cat.get("streams", []):
            iframe = s.get("iframe")
            if not iframe:
                continue

            starts = s.get("starts_at", 0)
            is_live = starts <= now and starts > 0

            final_cat = cname
            if cname.lower() == "football":
                final_cat = detect_football(s.get("name",""))

            categories = [final_cat]
            if is_live:
                categories.append("Live Now")

            flat.append({
                "id": s["id"],
                "name": s["name"],
                "iframe": iframe,
                "poster": s.get("poster") or BACKUP_LOGOS.get(final_cat.split(" - ")[0], ""),
                "time": get_time_wib(starts),
                "categories": categories
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
                s["url"] = next(iter(urls))   # ← NON RESTREAM VERSION
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

    print("DONE WRITING M3U")


if __name__ == "__main__":
    asyncio.run(main())
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
