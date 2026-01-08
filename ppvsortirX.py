# ppvsortirX.py
# FINAL PROFESSIONAL VERSION
# FOOTBALL TAG FIX + WIB TIME + LIVE NOW
# NON-RESTREAM | NO PROXY

import asyncio
import aiohttp
from playwright.async_api import async_playwright
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import time

API_URL = "https://api.ppv.to/api/streams"
PLAYLIST_FILE = "ppvsortirX.m3u"

STREAM_HEADERS = [
    '#EXTVLCOPT:http-referrer=https://ppv.to/',
    '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
]

GROUP_RENAME = {
    "Football - EPL": "PPVLand - Football - EPL",
    "Football - Serie A": "PPVLand - Football - Serie A",
    "Football - Bundesliga": "PPVLand - Football - Bundesliga",
    "Football - LaLiga": "PPVLand - Football - LaLiga",
    "Football - Ligue 1": "PPVLand - Football - Ligue 1",
    "Football - UCL": "PPVLand - Football - UCL",
    "Football - UEL": "PPVLand - Football - UEL",
    "Football - Other": "PPVLand - Football - Other",
    "Live Now": "PPVLand - Live Now",
    "Basketball": "PPVLand - Basketball",
    "Wrestling": "PPVLand - Wrestling",
    "Ice Hockey": "PPVLand - Ice Hockey",
    "American Football": "PPVLand - NFL",
    "Combat Sports": "PPVLand - Combat Sports",
    "Motorsports": "PPVLand - Motorsports",
    "Baseball": "PPVLand - Baseball",
    "Darts": "PPVLand - Darts",
    "Cricket": "PPVLand - Cricket"
}

# ======================
# FOOTBALL DETECTOR (FIXED)
# ======================
def detect_football(stream: dict) -> str:
    tag = (stream.get("tag") or "").lower()
    uri = (stream.get("uri_name") or "").lower()

    TAG_MAP = {
        "premier league": "Football - EPL",
        "serie a": "Football - Serie A",
        "bundesliga": "Football - Bundesliga",
        "laliga": "Football - LaLiga",
        "ligue 1": "Football - Ligue 1",
        "champions league": "Football - UCL",
        "europa league": "Football - UEL"
    }

    for k, v in TAG_MAP.items():
        if k in tag:
            return v

    if uri.startswith("premierleague/"):
        return "Football - EPL"
    if uri.startswith("seriea/"):
        return "Football - Serie A"
    if uri.startswith("bundesliga/"):
        return "Football - Bundesliga"
    if uri.startswith("laliga/"):
        return "Football - LaLiga"

    return "Football - Other"


def get_time_wib(ts: int) -> str:
    if not ts or ts <= 0:
        return ""
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.astimezone(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y %H:%M WIB")


async def fetch_streams():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, timeout=20) as r:
                data = await r.json()
                return data.get("streams", [])
    except Exception as e:
        print("API ERROR:", e)
        return []


async def grab_m3u8(page, url):
    found = None

    await page.route(
        "**/*",
        lambda r: r.abort()
        if r.request.resource_type in ["image", "stylesheet", "font"]
        else r.continue_()
    )

    def on_response(res):
        nonlocal found
        if ".m3u8" in res.url and not found:
            found = res.url

    page.on("response", on_response)

    try:
        await page.goto(url, timeout=8000)
    except:
        pass

    for _ in range(120):
        if found:
            break
        await asyncio.sleep(0.05)

    return found


async def main():
    streams = await fetch_streams()
    if not streams:
        print("NO STREAMS")
        return

    now = int(time.time())
    items = []

    for cat in streams:
        cname = cat.get("category", "")
        if cname.lower() == "24/7 streams":
            continue

        for s in cat.get("streams", []):
            iframe = s.get("iframe")
            if not iframe:
                continue

            starts = s.get("starts_at", 0)
            is_live = starts > 0 and starts <= now

            categories = []

            if cname.lower() == "football":
                categories.append(detect_football(s))
            else:
                categories.append(cname)

            if is_live:
                categories.append("Live Now")

            items.append({
                "id": s["id"],
                "name": s["name"],
                "iframe": iframe,
                "logo": s.get("poster", ""),
                "time": get_time_wib(starts),
                "categories": categories
            })

    items.sort(key=lambda x: x["name"].lower())

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        results = []

        for item in items:
            page = await browser.new_page()
            m3u8 = await grab_m3u8(page, item["iframe"])
            await page.close()

            if m3u8:
                item["url"] = m3u8
                results.append(item)

        await browser.close()

    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for it in results:
            for cat in it["categories"]:
                group = GROUP_RENAME.get(cat, cat)
                title = it["name"]
                if it["time"]:
                    title += f" - {it['time']}"

                f.write(
                    f'#EXTINF:-1 tvg-id="ppv-{it["id"]}" tvg-logo="{it["logo"]}" '
                    f'group-title="{group}",{title}\n'
                )
                for h in STREAM_HEADERS:
                    f.write(h + "\n")
                f.write(it["url"] + "\n")

    print("DONE →", PLAYLIST_FILE)


if __name__ == "__main__":
    asyncio.run(main())
