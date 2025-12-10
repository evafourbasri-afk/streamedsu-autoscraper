import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta

API_URL = "https://api.ppv.to/api/streams"
OUTPUT = "ppvsort.m3u"


# ============================
# WIB FORMAT
# ============================
def to_wib(ts):
    try:
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc) + timedelta(hours=7)
        return dt.strftime("%d %b %Y %H:%M WIB")
    except:
        return ""


# ============================
# CATEGORY DETECTOR
# ============================
def detect_category(title):
    t = title.lower()

    if "premier" in t or "epl" in t:
        return "Football - EPL"
    if "bundes" in t:
        return "Football - Bundesliga"
    if "serie" in t:
        return "Football - Serie A"
    if "liga" in t or "laliga" in t:
        return "Football - LaLiga"
    if "ligue" in t:
        return "Football - Ligue 1"
    if "ucl" in t or "champions" in t:
        return "Football - UCL"

    if "ufc" in t or "fight" in t:
        return "Combat Sports"
    if "wwe" in t or "wrestling" in t:
        return "Wrestling"

    return "Other"


# ============================
# LIVE CHECKER
# ============================
def is_live(start_ts, end_ts):
    now = int(datetime.now(timezone.utc).timestamp())
    try:
        start_ts = int(start_ts)
        end_ts = int(end_ts) if end_ts else start_ts + 3 * 3600
        return start_ts <= now <= end_ts
    except:
        return False


# ============================
# FETCH API
# ============================
async def fetch_streams():
    async with aiohttp.ClientSession() as s:
        async with s.get(API_URL) as r:
            if r.status != 200:
                return None
            return await r.json()


# ============================
# M3U GENERATOR
# ============================
async def generate():
    data = await fetch_streams()
    if not data:
        print("API error")
        return

    categories = data.get("streams", [])
    final_list = []

    # Flatten streams
    for cat in categories:
        group = cat.get("category", "Unknown")
        for s in cat.get("streams", []):
            final_list.append({
                "title": s.get("name"),
                "iframe": s.get("iframe"),
                "poster": s.get("poster"),
                "start": s.get("starts_at"),
                "end": s.get("ends_at"),
                "category": group
            })

    final_list.sort(key=lambda x: x["start"] or 0)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in final_list:
            title = item["title"]
            iframe = item["iframe"]
            poster = item["poster"]
            start = item["start"]
            end = item["end"]
            wib = to_wib(start)
            cat = detect_category(title)

            if not iframe:
                continue

            # Original category
            f.write(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{cat}",{title} - {wib}\n')
            f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
            f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
            f.write(iframe + "\n")

            # LIVE NOW duplicate
            if is_live(start, end):
                f.write(f'#EXTINF:-1 tvg-logo="{poster}" group-title="LIVE NOW",{title} - LIVE NOW\n')
                f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
                f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
                f.write(iframe + "\n")

    print("DONE → ppvsort.m3u created!")


asyncio.run(generate())
