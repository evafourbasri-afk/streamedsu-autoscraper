import aiohttp
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import re

PPV_API = "https://api.ppv.to/api/events/live"

# =============================
# 🔥 Mapping berdasarkan prefix URL
# =============================
PREFIX_MAP = {
    "epl_": "Football - EPL",
    "seriea_": "Football - Serie A",
    "bundesliga_": "Football - Bundesliga",
    "ligue1_": "Football - Ligue 1",
    "laliga_": "Football - LaLiga",
    "ucl_": "Football - UCL",
    "uel_": "Football - UEL",
    "uecl_": "Football - UECL",

    # PPVLand Sports
    "nfl": "PPVLand - NFL",
    "nba": "PPVLand - Basketball",
    "nhl": "PPVLand - Ice Hockey",
    "ufc": "PPVLand - Combat Sports",
    "wrestling": "PPVLand - Wrestling",
}


# =============================
# 🔥 Deteksi kategori berdasarkan URL M3U8
# =============================
def detect_category(stream_url: str) -> str:
    try:
        slug = stream_url.split("poocloud.in/")[1].split("/")[0]
    except:
        return "Football - Other"

    for prefix, cat in PREFIX_MAP.items():
        if slug.startswith(prefix):
            return cat

    return "Football - Other"


# =============================
# 🔥 Convert UTC → WIB
# =============================
def to_wib(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        wib = dt.astimezone(ZoneInfo("Asia/Jakarta"))
        return wib.strftime("%d %b %Y %H:%M WIB")
    except:
        return "Unknown Time"


# =============================
# 🔥 MAIN SCRAPER
# =============================
async def fetch_ppv():
    async with aiohttp.ClientSession() as session:
        async with session.get(PPV_API) as r:
            if r.status != 200:
                return None
            return await r.json()


async def generate_m3u():
    data = await fetch_ppv()
    if not data:
        print("API ERROR")
        return

    events = data.get("data", [])
    events_sorted = sorted(events, key=lambda x: x.get("startTime", ""))

    with open("ppvsort.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in events_sorted:
            title = item.get("title", "Untitled Event")
            poster = item.get("poster", "")
            event_id = item.get("id", "")
            start_time = to_wib(item.get("startTime", ""))

            # STREAM URL
            stream = item.get("streams", [{}])[0].get("url", "")

            # KATEGORI 🔥 sudah akurat
            group = detect_category(stream)

            # Tulis playlist
            f.write(f'#EXTINF:-1 tvg-id="ppv-{event_id}" tvg-logo="{poster}" group-title="{group}",{title} - {start_time}\n')
            f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
            f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)\n")
            f.write(f"{stream}\n")

    print("DONE → ppvsort.m3u updated.")


asyncio.run(generate_m3u())
