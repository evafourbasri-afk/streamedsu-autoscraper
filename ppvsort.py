import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta

API_URL = "https://api.ppv.to/api/streams"
OUTPUT = "ppvsort.m3u"

# ============================
# WIB TIME FORMATTER
# ============================
def to_wib(ts):
    try:
        ts = int(ts)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc) + timedelta(hours=7)
        return dt.strftime("%d %b %Y %H:%M WIB")
    except:
        return "Unknown Time"

# ============================
# KLASIFIKASI KATEGORI
# ============================
def detect_category(title):
    t = title.lower()

    if "epl" in t or "premier" in t:
        return "Football - EPL"
    if "bundes" in t:
        return "Football - Bundesliga"
    if "serie a" in t or "juventus" in t or "inter" in t:
        return "Football - Serie A"
    if "laliga" in t or "la liga" in t or "barcelona" in t or "real madrid" in t:
        return "Football - LaLiga"
    if "ligue" in t or "psg" in t:
        return "Football - Ligue 1"

    if "ucl" in t or "champions" in t:
        return "Football - UCL"
    if "uel" in t:
        return "Football - UEL"
    if "uecl" in t or "conference" in t:
        return "Football - UECL"

    if "ufc" in t or "fight" in t:
        return "Combat Sports"
    if "wwe" in t or "wrestling" in t:
        return "Wrestling"
    if "nba" in t or "basket" in t:
        return "Basketball"
    if "nhl" in t or "hockey" in t:
        return "Ice Hockey"
    if "nfl" in t:
        return "NFL"

    return "Other Sports"

# ============================
# DETECT LIVE NOW
# ============================
def is_live(start_ts, end_ts):
    now = datetime.now(timezone.utc).timestamp()

    try:
        start_ts = int(start_ts or 0)
        end_ts = int(end_ts) if end_ts else start_ts + 3 * 3600
        return start_ts <= now <= end_ts
    except:
        return False

# ============================
# FETCH STREAMS API
# ============================
async def fetch_streams():
    async with aiohttp.ClientSession() as s:
        async with s.get(API_URL) as r:
            if r.status != 200:
                print("API Error:", r.status)
                return None
            return await r.json()

# ============================
# BUILD M3U
# ============================
async def generate_m3u():
    data = await fetch_streams()
    if not data:
        print("Fetch API gagal.")
        return

    streams = data.get("data", [])

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in streams:

            title = item.get("title", "Unknown Event")
            poster = item.get("poster", "")
            event_id = item.get("id", "")
            start = item.get("startTime")
            end = item.get("endTime")
            start_wib = to_wib(start)

            stream_data = item.get("stream", {})
            stream = stream_data.get("url", "")

            if not stream:
                continue

            category = detect_category(title)

            # Entry utama
            f.write(
                f'#EXTINF:-1 tvg-id="ppv-{event_id}" tvg-logo="{poster}" group-title="{category}",'
                f'{title} - {start_wib}\n'
            )
            f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
            f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
            f.write(stream + "\n")

            # LIVE NOW versi duplikat
            if is_live(start, end):
                f.write(
                    f'#EXTINF:-1 tvg-id="ppv-{event_id}" tvg-logo="{poster}" '
                    f'group-title="LIVE NOW",{title} - LIVE NOW\n'
                )
                f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
                f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
                f.write(stream + "\n")

    print("DONE → ppvsort.m3u created.")

asyncio.run(generate_m3u())
