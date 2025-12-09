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
        return ""

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
    if "laliga" in t or "barcelona" in t or "real madrid" in t:
        return "Football - LaLiga"
    if "ligue" in t or "psg" in t:
        return "Football - Ligue 1"

    if "ucl" in t or "champions" in t:
        return "Football - UCL"
    if "uel" in t:
        return "Football - UEL"
    if "uecl" in t or "conference" in t:
        return "Football - UECL"

    if "nfl" in t:
        return "PPVLand - NFL"
    if "hockey" in t:
        return "PPVLand - Ice Hockey"
    if "wrestling" in t or "wwe" in t or "aew" in t:
        return "PPVLand - Wrestling"
    if "ufc" in t or "fight" in t:
        return "PPVLand - Combat Sports"
    if "nba" in t or "basket" in t:
        return "PPVLand - Basketball"

    return "PPVLand - Other"

# ============================
# DETECT LIVE NOW
# ============================
def is_live(start_ts, end_ts):
    now = datetime.now(timezone.utc).timestamp()
    try:
        start_ts = int(start_ts or 0)
        end_ts = int(end_ts) if end_ts else start_ts + 3 * 3600  # fallback 3 jam

        return start_ts <= now <= end_ts
    except:
        return False

# ============================
# FETCH STREAM API
# ============================
async def fetch_streams():
    async with aiohttp.ClientSession() as s:
        async with s.get(API_URL) as r:
            if r.status != 200:
                print("API ERROR:", r.status)
                return None
            return await r.json()

# ============================
# GENERATE M3U
# ============================
async def generate_m3u():
    json_data = await fetch_streams()
    if not json_data:
        print("Gagal mengambil data dari API.")
        return

    streams = json_data.get("data", [])
    if not streams:
        print("API kosong!")
        return

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in streams:
            title = item.get("title", "Untitled")
            poster = item.get("poster", "")
            event_id = item.get("id", "")
            s_time = item.get("startTime")
            e_time = item.get("endTime")

            start_wib = to_wib(s_time)

            # Ambil URL HLS dari API STREAM
            stream = item.get("stream", {}).get("url", "")

            if not stream:
                continue

            category = detect_category(title)

            # ➜ Tulis entry utama
            f.write(f'#EXTINF:-1 tvg-id="ppv-{event_id}" tvg-logo="{poster}" group-title="{category}",{title} - {start_wib}\n')
            f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
            f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
            f.write(stream + "\n")

            # ➜ Tulis entry LIVE NOW
            if is_live(s_time, e_time):
                f.write(f'#EXTINF:-1 tvg-id="ppv-{event_id}" tvg-logo="{poster}" group-title="LIVE NOW",{title} - ⛔ LIVE NOW\n')
                f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
                f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
                f.write(stream + "\n")

    print("DONE → ppvsort.m3u berhasil dibuat.")


asyncio.run(generate_m3u())
