# PPVSort FastMode+ (Stable m3u8)
# Cepat, stabil, tanpa LIVE NOW, hasil m3u8/mpd terjamin

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
    "Cricket": "PPV - Cricket"
}


def detect_football(name):
    name = name.lower()
    for league, keys in FOOTBALL_MAP.items():
        if any(k in name for k in keys):
            return f"Football - {league}"
    return "Football - Other"


def get_time_wib(ts):
    if not ts or ts <= 0:
        return ""
    dt = datetime.fromtimestamp(ts, timezone.utc)
    dt_wib = dt.astimezone(ZoneInfo("Asia/Jakarta"))
    return dt_wib.strftime("%d %b %Y %H:%M WIB")


async def fetch_streams():
    try:
        async with aiohttp.ClientSession() as s:
            r = await s.get(API_URL, timeout=15)
            return (await r.json()).get("streams", [])
    except:
        return []


async def grab_m3u8(page, iframe):
    found = None

    # Header agar player cepat load
    await page.set_extra_http_headers({
        "Referer": "https://ppv.to/",
        "User-Agent": "Mozilla/5.0"
    })

    # Blokir yang tidak perlu (hemat waktu)
    await page.route(
        "**/*",
        lambda r: r.abort()
        if r.request.resource_type in ["image", "font", "stylesheet", "media"]
        else r.continue_()
    )

    def on_res(res):
        nonlocal found
        if (".m3u8" in res.url or ".mpd" in res.url) and not found:
            found = res.url

    page.on("response", on_res)

    try:
        await page.goto(iframe, timeout=8000)  # lebih tinggi agar m3u8 muncul
    except:
        pass

    # FASTMODE+: tunggu maksimal ±8 detik (160 * 0.05)
    for _ in range(160):
        if found:
            return found
        await asyncio.sleep(0.05)

    return None  # tidak retry, tetap cepat


async def main():
    streams = await fetch_streams()
    if not streams:
        print("NO STREAMS AVAILABLE")
        return

    flat = []

    for category in streams:
        cname = category.get("category", "").strip()

        if cname.lower() == "24/7 streams":
            continue

        for s in category.get("streams", []):
            iframe = s.get("iframe")
            if not iframe:
                continue

            final_cat = cname
            if cname.lower() == "football":
                final_cat = detect_football(s.get("name", ""))

            flat.append({
                "id": s["id"],
                "name": s["name"],
                "iframe": iframe,
                "poster": s.get("poster") or "",
                "time": get_time_wib(s.get("starts_at", 0)),
                "category": final_cat
            })

    # sort by name
    flat.sort(key=lambda x: x["name"].lower())

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for item in flat:
            page = await browser.new_page()

            url = await grab_m3u8(page, item["iframe"])

            await page.close()

            # Jika gagal → BUANG (tidak pakai iframe)
            if not url:
                continue

            item["url"] = url
            results.append(item)

        await browser.close()

    # Write output
    with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in results:
            group = GROUP_RENAME_MAP.get(item["category"], item["category"])

            title = item["name"]
            if item["time"]:
                title += f" - {item['time']}"

            f.write(
                f'#EXTINF:-1 tvg-id="{item["id"]}" '
                f'tvg-logo="{item["poster"]}" '
                f'group-title="{group}",{title}\n'
            )

            for h in STREAM_HEADERS:
                f.write(h + "\n")

            f.write(item["url"] + "\n")

    print("FASTMODE+ DONE →", PLAYLIST_FILE)


if __name__ == "__main__":
    asyncio.run(main())
