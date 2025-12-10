import json
import requests
from io import BytesIO
from PIL import Image, ImageDraw
from datetime import datetime
from zoneinfo import ZoneInfo

# ===========================
# CONFIG
# ===========================
BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"
OUTPUT_FILE = "NewPixel.m3u8"

EVENT_LOGOS = {
    "NBA": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NBA.png",
    "NHL": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NHL.png",
    "NFL": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NFL.png",
    "MLB": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/MLB.png",
}

TEAM_SCALE = 0.85
EVENT_SCALE = 0.70
PADDING = 50
CANVAS_PADDING = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": BASE + "/",
}


# ===========================
# WIB TIME FORMATTER
# ===========================
def convert_to_wib(utc_timestamp_ms):
    try:
        utc_dt = datetime.fromtimestamp(utc_timestamp_ms / 1000, tz=ZoneInfo("UTC"))
        wib_dt = utc_dt.astimezone(ZoneInfo("Asia/Jakarta"))
        return wib_dt.strftime("%d %b %H:%M WIB")
    except:
        return ""


# ===========================
# IMAGE HELPERS
# ===========================
def download_image(url):
    try:
        r = requests.get(url, timeout=10)
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except:
        return None


def resize_logo(img, scale):
    if img is None:
        return None
    w, h = img.size
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def generate_thumbnail(team1_logo, event_logo, team2_logo, out_name):
    try:
        t1 = download_image(team1_logo)
        e = download_image(event_logo)
        t2 = download_image(team2_logo)

        if t1 is None or t2 is None:
            return None

        t1 = resize_logo(t1, TEAM_SCALE)
        t2 = resize_logo(t2, TEAM_SCALE)
        if e:
            e = resize_logo(e, EVENT_SCALE)

        w1, h1 = t1.size
        w2, h2 = t2.size
        we, he = e.size if e else (0, 0)

        width = CANVAS_PADDING + w1 + PADDING + we + PADDING + w2 + CANVAS_PADDING
        height = max(h1, h2, he) + CANVAS_PADDING * 2

        canvas = Image.new("RGBA", (width, height), (32, 32, 32, 255))

        x = CANVAS_PADDING
        y = (height - h1) // 2
        canvas.paste(t1, (x, y), t1)

        x += w1 + PADDING
        if e:
            ye = (height - he) // 2
            canvas.paste(e, (x, ye), e)
            x += we + PADDING

        y2 = (height - h2) // 2
        canvas.paste(t2, (x, y2), t2)

        save_path = f"thumbs/{out_name}.png"
        canvas.save(save_path, format="PNG")
        return save_path
    except:
        return None


# ===========================
# PIXELSPORT EVENT SCRAPER
# ===========================
def get_league(ev):
    name = ev.get("channel", {}).get("TVCategory", {}).get("name", "").upper()

    if "NBA" in name: return "NBA"
    if "NHL" in name: return "NHL"
    if "NFL" in name: return "NFL"
    if "MLB" in name: return "MLB"
    return "Other"


def scrape_pixelsport():
    events = requests.get(API_EVENTS, headers=HEADERS, timeout=10).json().get("events", [])
    sliders = requests.get(API_SLIDERS, headers=HEADERS, timeout=10).json().get("data", [])
    return events, sliders


# ===========================
# BUILD M3U
# ===========================
def build_m3u(events, sliders):
    out = ["#EXTM3U"]

    for ev in events:
        title = ev.get("match_name", "Unknown Event")
        ts = ev.get("startTimeStamp")
        wib_time = convert_to_wib(ts) if ts else ""
        if wib_time:
            title = f"{wib_time} - {title}"

        league = get_league(ev)
        event_logo = EVENT_LOGOS.get(league, None)

        t1_logo = ev.get("competitors1_logo")
        t2_logo = ev.get("competitors2_logo")

        thumb_name = f"{ev.get('id','event')}_{league}"
        thumb_path = generate_thumbnail(t1_logo, event_logo, t2_logo, thumb_name)

        tvg_logo = f"https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/{thumb_path}" if thumb_path else t1_logo

        links = []
        chan = ev.get("channel", {})
        for i in range(1, 4):
            u = chan.get(f"server{i}URL")
            if u and u.lower() != "null":
                links.append(u)

        for url in links:
            out.append(f'#EXTINF:-1 tvg-logo="{tvg_logo}" group-title="PixelSport - {league}",{title}')
            out.append(url)

    # SLIDER LIVE TV SECTION
    for sl in sliders:
        links = []
        lv = sl.get("liveTV", {})
        for i in range(1, 4):
            u = lv.get(f"server{i}URL")
            if u and u.lower() != "null":
                links.append(u)

        for u in links:
            out.append(f'#EXTINF:-1 tvg-logo="{EVENT_LOGOS.get("NFL")}" group-title="PixelSport - Live",{sl.get("title","Live")}')
            out.append(u)

    return "\n".join(out)


# ===========================
# MAIN
# ===========================
def main():
    try:
        events, sliders = scrape_pixelsport()
        m3u = build_m3u(events, sliders)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(m3u)

        print(f"[OK] {OUTPUT_FILE} generated successfully.")
    except Exception as e:
        print("[ERROR]", e)


if __name__ == "__main__":
    main()
