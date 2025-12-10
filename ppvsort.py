import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta

API_URL = "https://api.ppv.to/api/streams"
OUTPUT = "ppvsort.m3u"

PROXY_BASE = "https://panel1.ogie.shop:8181/m3u/proxy.php?u="


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
def detect_category(title, raw_cat):
    t = title.lower()
    rc = raw_cat.lower()

    # FOOTBALL
    if "ucl" in t or "champions" in t:
        return "Football - UCL"
    if "uel" in t or "europa" in t:
        return "Football - UEL"
    if "uecl" in t or "conference" in t:
        return "Football - UECL"
    if any(x in t for x in ["premier league", "epl", "man ", "arsenal", "chelsea", "liverpool"]):
        return "Football - EPL"
    if "bundes" in t or "bayern" in t or "dortmund" in t:
        return "Football - Bundesliga"
    if "serie a" in t or "juventus" in t or "milan" in t:
        return "Football - Serie A"
    if "ligue" in t or "psg" in t:
        return "Football - Ligue 1"
    if "laliga" in t or "la liga" in t:
        return "Football - LaLiga"

    # OTHER SPORTS
    if "nba" in rc or "basket" in rc:
        return "Basketball"
    if "nhl" in rc or "hockey" in rc:
        return "Hockey"
    if "nfl" in rc or "football" in rc:
        return "American Football"

    if "ufc" in t or "fight" in t or "mma" in t:
        return "Combat Sports"

    if "wwe" in t or "aew" in t or "tna" in t:
        return "Wrestling"

    return "Other"


# ============================
# LIVE CHECKER
# ============================
def is_live(start_ts, end_ts):
    now = int(datetime.now(timezone.utc).timestamp())
    try:
        start_ts = int(start_ts)
        if not end_ts:
            end_ts = start_ts + 3 * 3600
        else:
            end_ts = int(end_ts)
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
                print("API Error:", r.status)
                return None
            return await r.json()


# ============================
# GENERATE M3U
# ============================
async def generate():
    data = await fetch_streams()
    if not data:
        print("API EMPTY")
        return

    categories = data.get("streams", [])
    final_list = []

    # FLATTEN LIST
    for cat in categories:
        raw_cat = cat.get("category", "")

        for s in cat.get("streams", []):
            title = s.get("name", "")
            iframe = s.get("iframe", "")
            poster = s.get("poster", "")
            start = s.get("starts_at", 0)
            end = s.get("ends_at", 0)

            # SKIP 24/7 CHANNELS
            if "24/7" in title or "24x7" in title:
                continue

            final_list.append({
                "title": title,
                "iframe": iframe,
                "poster": poster,
                "start": start,
                "end": end,
                "raw_category": raw_cat,
            })

    # SORT BY START TIME
    final_list.sort(key=lambda x: x["start"] or 0)

    # WRITE M3U
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in final_list:
            title = item["title"]
            iframe = item["iframe"]
            poster = item["poster"]
            start = item["start"]
            end = item["end"]
            wib = to_wib(start)

            category = detect_category(title, item["raw_category"])

            # Convert stream through proxy
            proxied = PROXY_BASE + iframe

            # MAIN ENTRY
            f.write(
                f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{title} - {wib}\n'
            )
            f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
            f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
            f.write(proxied + "\n")

            # LIVE NOW ENTRY
            if is_live(start, end):
                f.write(
                    f'#EXTINF:-1 tvg-logo="{poster}" group-title="LIVE NOW",{title} 🔴 LIVE NOW\n'
                )
                f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
                f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
                f.write(proxied + "\n")

    print("DONE → ppvsort.m3u CREATED")


asyncio.run(generate())
