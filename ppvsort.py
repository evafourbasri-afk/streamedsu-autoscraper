import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta

PPV_API = "https://api.ppv.to/api/events"
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
# KLASIFIKASI LIGA
# ============================
def detect_category(title):
    T = title.lower()

    if any(x in T for x in ["premier", "epl", "arsenal", "chelsea", "liverpool", "man "]):
        return "Football - EPL"
    if any(x in T for x in ["bundesliga", "bayern", "dortmund"]):
        return "Football - Bundesliga"
    if any(x in T for x in ["serie a", "juventus", "inter", "milan"]):
        return "Football - Serie A"
    if any(x in T for x in ["laliga", "la liga", "real madrid", "barcelona"]):
        return "Football - LaLiga"
    if any(x in T for x in T for x in ["ligue 1", "psg", "marseille", "lille"]):
        return "Football - Ligue 1"

    if "ucl" in T or "champions" in T:
        return "Football - UCL"
    if "uel" in T or "europa league" in T:
        return "Football - UEL"
    if "conference" in T or "uecl" in T:
        return "Football - UECL"

    return "Football - Other"

# ============================
# DETECT LIVE NOW
# ============================
def is_live(start_ts, end_ts):
    now = datetime.now(timezone.utc).timestamp()
    try:
        if not start_ts:
            return False
        start_ts = int(start_ts)

        # Jika tidak ada endTime → anggap LIVE selama 4 jam
        if not end_ts:
            return start_ts <= now <= start_ts + 4*3600

        end_ts = int(end_ts)
        return start_ts <= now <= end_ts
    except:
        return False

# ============================
# FETCH API
# ============================
async def fetch_ppv():
    async with aiohttp.ClientSession() as session:
        async with session.get(PPV_API) as r:
            if r.status != 200:
                return None
            return await r.json()

# ============================
# M3U GENERATOR
# ============================
async def generate():
    data = await fetch_ppv()
    if not data:
        print("API ERROR")
        return

    events = data.get("data", [])
    events_sorted = sorted(events, key=lambda x: x.get("startTime", 0))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for e in events_sorted:

            title = e.get("title", "Unknown Event")
            poster = e.get("poster", "")
            event_id = e.get("id", "")
            start = e.get("startTime", 0)
            end = e.get("endTime", 0)
            start_wib = to_wib(start)
            iframe = e.get("iframe", "")

            if not iframe:
                continue

            # kategori utama
            cat = detect_category(title)

            # ======================
            # 1️⃣ TULIS ENTRY KATEGORI ASLI
            # ======================
            f.write(f'#EXTINF:-1 tvg-id="ppv-{event_id}" tvg-logo="{poster}" group-title="{cat}",{title} - {start_wib}\n')
            f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
            f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
            f.write(f"{iframe}\n")

            # ======================
            # 2️⃣ TULIS ENTRY LIVE NOW (DUPLIKAT)
            # ======================
            if is_live(start, end):
                f.write(f'#EXTINF:-1 tvg-id="ppv-{event_id}" tvg-logo="{poster}" group-title="LIVE NOW",{title} - LIVE NOW\n')
                f.write("#EXTVLCOPT:http-referrer=https://ppv.to/\n")
                f.write("#EXTVLCOPT:http-user-agent=Mozilla/5.0\n")
                f.write(f"{iframe}\n")

    print("DONE → ppvsort.m3u created.")


asyncio.run(generate())
