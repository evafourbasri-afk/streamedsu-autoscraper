# ppvsortir_wib.py
# FINAL CLEAN NON-RESTREAM VERSION (NO PROXY)
# WIB TIME + FOOTBALL SUBCATEGORY + SORTING + LIVE NOW

import asyncio
from playwright.async_api import async_playwright
import aiohttp
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import time

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
    "Cricket": "http://drewlive2423.duckdns.org:9000/Logos/Cricket.png"
}

GROUP_RENAME_MAP = {
    "Wrestling": "PPVLand - Wrestling",
    "Football": "PPVLand - Football",
    "Basketball": "PPVLand - Basketball",
    "Baseball": "PPVLand - Baseball",
    "American Football": "PPVLand - NFL",
    "Combat Sports": "PPVLand - Combat Sports",
    "Darts": "PPVLand - Darts",
    "Motorsports": "PPVLand - Motorsports",
    "Live Now": "PPVLand - Live Now",
    "Ice Hockey": "PPVLand - Ice Hockey",
    "Cricket": "PPVLand - Cricket"
}

FOOTBALL_MAP = {
    "EPL": ["premier", "epl", "premierleague", "england"],
    "Serie A": ["serie a", "Serie A", "italy"],
    "Bundesliga": ["bundesliga", "germany"],
    "LaLiga": ["laliga", "LaLuga", "la liga", "spain"],
    "Ligue 1": ["ligue 1"],
    "UCL": ["champions league", "ucl"],
    "UEL": ["europa league", "uel"],
    "MLS": ["mls"],
    "Libertadores": ["libertadores"]
}

def detect_football(name):
    name = name.lower()
    for league, keys in FOOTBALL_MAP.items():
        if any(k in name for k in keys):
            return f"Football - {league}"
    return "Football - Other"

def get_time_wib(starts_at):
    if not starts_at or starts_at <= 0:
        return ""
    dt = datetime.fromtimestamp(starts_at, tz=timezone.utc)
    dt_wib = dt.astimezone(ZoneInfo("Asia/Jakarta"))
    return dt_wib.strftime("%d %b %Y %H:%M WIB")

async def safe_grab(page, url):
    try:
        return await asyncio.wait_for(grab_m3u8(page, url), timeout=10)
    except:
        return set()

async def grab_m3u8(page, iframe):
    first = None

    await page.route(
        "**/*",
        lambda r: r.abort() if r.request.resource_type in ["image", "stylesheet", "font", "media"] else r.continue_()
    )

    def on_response(res):
        nonlocal first
        if ".m3u8" in res.url and not first:
            first = res.url

    page.on("response", on_response)

    try:
        await page.goto(iframe, timeout=6000)
    except:
        pass

    for _ in range(150):
        if first:
            break
        await asyncio.sleep(0.05)

    return {first} if first else set()

async def fetch_streams():
    try:
        async with aiohttp.ClientSession() as session:
            r = await session.get(API_URL, timeout=20)
            j = await r.json()
            return j.get("streams", [])
    except:
        return []

async def main():
    streams = await fetch_streams()
    if not streams:
        print("NO STREAMS FOUND")
        return

    now = int(time.time())
    flat = []

    for category in streams:
        cname = category.get("category", "").strip()
        if cname.lower() == "24/7 streams":
            continue

        for s in category.get("streams", []):
            iframe = s.get("iframe")
            if not iframe:
                continue

            starts = s.get("starts_at", 0)
            is_live = starts > 0 and starts <= now

            final_cat = cname
            if cname.lower() == "football":
                final_cat = detect_football(s.get("name", ""))

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

        for item in flat:
            page = await browser.new_page()
            urls = await safe_grab(page, item["iframe"])
            await page.close()

            if urls:
                item["url"] = next(iter(urls))
                results.append(item)

        await browser.close()

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in results:
            for cat in item["categories"]:
                group = GROUP_RENAME_MAP.get(cat, cat)
                title = item["name"]
                if item["time"]:
                    title += f" - {item['time']}"

                f.write(
                    f'#EXTINF:-1 tvg-id="ppv-{item["id"]}" tvg-logo="{item["poster"]}" group-title="{group}",{title}\n'
                )

                for h in STREAM_HEADERS:
                    f.write(h + "\n")

                f.write(item["url"] + "\n")

    print("DONE — M3U GENERATED:", PLAYLIST_FILE)


if __name__ == "__main__":
    asyncio.run(main())
