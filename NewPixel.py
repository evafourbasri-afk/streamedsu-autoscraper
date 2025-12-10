import json
import requests
from io import BytesIO
from PIL import Image
from datetime import datetime
from zoneinfo import ZoneInfo

BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"
OUTPUT_FILE = "NewPixel.m3u8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": BASE + "/",
    "Origin": BASE,
    "Connection": "keep-alive",
}

EVENT_LOGOS = {
    "NBA": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NBA.png",
    "NHL": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NHL.png",
    "NFL": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NFL.png",
    "MLB": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/MLB.png",
}

# ==========================================================
#  SAFE REQUEST (ANTI ERROR + AUTO RETRY)
# ==========================================================
def safe_get_json(url, retries=3):
    for _ in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()  # PASTI JSON
            return data
        except:
            continue
    return {}  # Kembali kosong agar tidak error


# ==========================================================
#  WIB TIME
# ==========================================================
def convert_to_wib(timestamp_ms):
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=ZoneInfo("UTC"))
        wib = dt.astimezone(ZoneInfo("Asia/Jakarta"))
        return wib.strftime("%d %b %H:%M WIB")
    except:
        return ""


# ==========================================================
#  SCRAPE EVENTS
# ==========================================================
def get_league(ev):
    name = ev.get("channel", {}).get("TVCategory", {}).get("name", "").upper()
    if "NBA" in name: return "NBA"
    if "NHL" in name: return "NHL"
    if "NFL" in name: return "NFL"
    if "MLB" in name: return "MLB"
    return "Other"


# ==========================================================
#  FETCH EVENTS WITH SAFE JSON
# ==========================================================
def fetch_pixelsport():
    events = safe_get_json(API_EVENTS).get("events", [])
    sliders = safe_get_json(API_SLIDERS).get("data", [])
    return events, sliders


# ==========================================================
#  BUILD M3U
# ==========================================================
def build_m3u(events, sliders):
    out = ["#EXTM3U"]

    for ev in events:
        title = ev.get("match_name", "Unknown")
        ts = ev.get("startTimeStamp")
        if ts:
            title = f"{convert_to_wib(ts)} - {title}"

        league = get_league(ev)
        event_logo = EVENT_LOGOS.get(league)

        t1 = ev.get("competitors1_logo")
        t2 = ev.get("competitors2_logo")

        # thumbnails di-skip dulu agar fokus fix error JSON
        logo_final = t1 if t1 else ""

        links = []
        ch = ev.get("channel", {})
        for i in range(1, 4):
            u = ch.get(f"server{i}URL")
            if u and u != "null":
                links.append(u)

        for l in links:
            out.append(f'#EXTINF:-1 tvg-logo="{logo_final}" group-title="PixelSport - {league}",{title}')
            out.append(l)

    return "\n".join(out)


# ==========================================================
#  MAIN
# ==========================================================
def main():
    try:
        events, sliders = fetch_pixelsport()

        print(f"[INFO] Events fetched: {len(events)}")
        if len(events) == 0:
            print("[WARN] PixelSport returned NO EVENTS — API blocked/empty")

        m3u = build_m3u(events, sliders)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(m3u)

        print("[OK] NewPixel.m3u8 generated")

    except Exception as e:
        print("[FATAL ERROR]", e)


if __name__ == "__main__":
    main()
