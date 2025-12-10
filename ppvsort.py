# ppvsortir_final.py
# FIXED VERSION — Chromium + Retry + Guaranteed Output

import asyncio
from playwright.async_api import async_playwright
import aiohttp
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import time

API_URL = "https://api.ppv.to/api/streams"
PLAYLIST_FILE = "ppvsort.m3u"

STREAM_HEADERS = [
    '#EXTVLCOPT:http-referrer=https://ppv.to/',
    '#EXTVLCOPT:http-user-agent=Mozilla/5.0'
]

FOOTBALL_MAP = {
    "EPL": ["epl", "premier", "england"],
    "Serie A": ["serie a", "italy"],
    "Bundesliga": ["bundesliga", "germany"],
    "LaLiga": ["laliga", "la liga", "spain"],
    "Ligue 1": ["ligue 1", "france"]
}

GROUP_RENAME_MAP = {
    "Wrestling": "PPV - Wrestling",
    "Football": "PPV - Football",
    "Basketball": "PPV - Basketball",
    "Baseball": "PPV - Baseball",
    "American Football": "PPV - NFL",
    "Combat Sports": "PPV - Combat Sports",
    "Ice Hockey": "PPV - Ice Hockey",
    "Cricket": "PPV - Cricket",
    "Live Now": "PPV - Live Now"
}

async def fetch_streams():
    try:
        async with aiohttp.ClientSession() as session:
            r = await session.get(API_URL, timeout=20)
            j = await r.json()
            return j.get("streams", [])
    except:
        return []

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

async def grab_url(page, iframe):
    found = None

    await page.route(
        "**/*",
        lambda r: r.abort()
        if r.request.resource_type in ["image", "font", "stylesheet"]
        else r.continue_()
    )

    def on_response(res):
        nonlocal found
        if (".m3u8" in res.url or ".mpd" in res.url) and not found:
            found = res.url

    page.on("response", on_response)

    try:
        await page.goto(iframe, timeout=20000)
    except:
        pass

    for _ in range(200):
        if found:
            return found
        await asyncio.sleep(0.05)

    return None

async def main():
    streams = await fetch_streams()
    if not streams:
        print("NO STREAMS FOUND")
        return

    now = int(time.time())
    flat = []

    for category in streams:
        cname = category.get("category", "")

        if cname.lower() == "24/7 streams":
            continue

        for s in category.get("streams", []):
            iframe = s.get("iframe")
            if not iframe:
                continue

            starts = s.get("starts_at", 0)
            is_live = starts <= now and starts > 0

            final_cat = cname
            if cname.lower() == "football":
                final_cat = detect_football(s.get("name", ""))

            cats = [final_cat]
            if is_live:
                cats.append("Live Now")

            flat.append({
                "id": s["id"],
                "name": s["name"],
                "iframe": iframe,
                "poster": s.get("poster") or "",
                "time": get_time_wib(starts),
                "categories": cats
            })

    flat.sort(key=lambda x: x["name"])

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for item in flat:
            page = await browser.new_page()

            url = None
            for _ in range(3):
                url = await grab_url(page, item["iframe"])
                if url:
                    break

            await page.close()

            # Fallback jika gagal → tetap pakai iframe supaya tidak kosong
            item["url"] = url if url else item["iframe"]
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

                f.write(f'#EXTINF:-1 tvg-id="{item["id"]}" tvg-logo="{item["poster"]}" group-title="{group}",{title}\n')
                for h in STREAM_HEADERS:
                    f.write(h + "\n")
                f.write(item["url"] + "\n")

    print("DONE — FIXED M3U:", PLAYLIST_FILE)

if __name__ == "__main__":
    asyncio.run(main())
async def main():
    streams = await fetch_streams()
    if not streams:
        print("NO STREAMS FOUND")
        return

    now = int(time.time())
    flat = []

    for category in streams:
        cname = category.get("category", "").strip()

        # Remove 24/7
        if cname.lower() == "24/7 streams":
            continue

        for s in category.get("streams", []):
            iframe = s.get("iframe")
            if not iframe:
                continue

            starts = s.get("starts_at", 0)
            is_live = starts <= now and starts > 0

            final_cat = cname
            if cname.lower() == "football":
                final_cat = detect_football(s.get("name", ""))

            categories = [final_cat]
            if is_live:
                categories.append("Live Now")  # duplicate category A

            flat.append({
                "id": s["id"],
                "name": s["name"],
                "iframe": iframe,
                "poster": s.get("poster") or BACKUP_LOGOS.get(final_cat.split(" - ")[0], ""),
                "time": get_time_wib(starts),
                "categories": categories
            })

    # Sort by name
    flat.sort(key=lambda x: x["name"].lower())

    results = []

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)

        for item in flat:
            page = await browser.new_page()
            url = await grab_m3u8(page, item["iframe"])
            await page.close()

            if url:
                item["url"] = url
                results.append(item)

        await browser.close()

    # Write playlist
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
