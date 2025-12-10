import json
import urllib.request
from urllib.error import URLError, HTTPError
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image
import requests
from io import BytesIO

BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"
OUTPUT_FILE = "NewPixel.m3u8"

THUMB_FOLDER = "thumbs"
EVENT_LOGO_FOLDER = "event_logos"

# Pastikan folder ada
os.makedirs(THUMB_FOLDER, exist_ok=True)

VLC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
VLC_REFERER = f"{BASE}/"

# Event Logo Map (local GitHub folder)
EVENT_LOGO_MAP = {
    "NBA": f"{EVENT_LOGO_FOLDER}/NBA.png",
    "NFL": f"{EVENT_LOGO_FOLDER}/NFL.png",
    "MLB": f"{EVENT_LOGO_FOLDER}/MLB.png",
    "NHL": f"{EVENT_LOGO_FOLDER}/NHL.png",
}

LEAGUE_KEYWORDS = {
    "nba": "NBA",
    "basket": "NBA",
    "nfl": "NFL",
    "football": "NFL",
    "mlb": "MLB",
    "baseball": "MLB",
    "nhl": "NHL",
    "hockey": "NHL",
}

def detect_league(text):
    if not text:
        return "Other"
    t = text.lower()
    for k, v in LEAGUE_KEYWORDS.items():
        if k in t:
            return v
    return "Other"


def fetch_json(url):
    headers = {
        "User-Agent": VLC_USER_AGENT,
        "Referer": VLC_REFERER,
        "Accept": "*/*",
        "Connection": "close",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_image(url):
    try:
        r = requests.get(url, timeout=8)
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        return img
    except:
        return None


def merge_logos(logo1_url, event_logo_url, logo2_url, filename):

    img1 = load_image(logo1_url)
    img2 = load_image(logo2_url)
    evt = load_image(event_logo_url)

    # Resize kecil seperti versi awal launcher
    if img1 is None:
        img1 = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    else:
        img1 = img1.resize((80, 80))

    if img2 is None:
        img2 = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    else:
        img2 = img2.resize((80, 80))

    if evt is None:
        evt = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    else:
        evt = evt.resize((60, 60))

    # canvas final total 220x80 → tampilan kecil rapi
    W = 220
    H = 80
    canvas = Image.new("RGBA", (W, H), (20, 20, 20, 255))

    # Home
    canvas.paste(img1, (0, 0), img1)

    # Event Logo di tengah
    canvas.paste(evt, (80, 10), evt)

    # Away
    canvas.paste(img2, (140, 0), img2)

    save_path = f"{THUMB_FOLDER}/{filename}.png"
    canvas.save(save_path)
    return save_path


def format_wib(dt_str):
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        wib = dt.astimezone(ZoneInfo("Asia/Jakarta"))
        return wib.strftime("%d %b %Y %H:%M WIB")
    except:
        return ""


def collect_links(channel_obj):
    links = []
    if not channel_obj:
        return links

    for i in range(1, 4):
        url = channel_obj.get(f"server{i}URL")
        if url and url.lower() != "null":
            links.append(url)

    return links


def build_m3u(events, sliders):
    out = ["#EXTM3U"]

    for ev in events:
        title = ev.get("match_name", "Unknown Event").strip()

        t1 = ev.get("competitors1_logo")
        t2 = ev.get("competitors2_logo")

        raw_cat = ev.get("channel", {}).get("TVCategory", {}).get("name", "")
        league = detect_league(raw_cat)

        event_logo = EVENT_LOGO_MAP.get(league, None)

        start_time = ev.get("start_date")
        wib_time = format_wib(start_time)

        final_title = f"{title} | {wib_time}"

        filename = f"{league}_{title.replace(' ', '_')[:40]}"
        merged = merge_logos(t1, event_logo, t2, filename)

        raw_github = f"https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/{merged}"

        links = collect_links(ev.get("channel", {}))
        if not links:
            continue

        for link in links:
            out.append(f'#EXTINF:-1 tvg-logo="{raw_github}" group-title="PixelSport - {league}",{final_title}')
            out.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            out.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            out.append(link)

    # SLIDERS
    for ch in sliders:
        title = ch.get("title", "Live Channel")
        live = ch.get("liveTV", {})
        links = collect_links(live)
        if not links:
            continue

        for link in links:
            out.append(f'#EXTINF:-1 tvg-logo="{EVENT_LOGO_MAP.get("NBA")}" group-title="PixelSport - Live",{title}')
            out.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            out.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            out.append(link)

    return "\n".join(out)


def main():
    try:
        print("[*] Fetching events...")
        events = fetch_json(API_EVENTS).get("events", [])

        print("[*] Fetching sliders...")
        sliders = fetch_json(API_SLIDERS).get("data", [])

        m3u = build_m3u(events, sliders)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(m3u)

        print(f"[✓] Saved {OUTPUT_FILE}")
    except Exception as e:
        print("[X] ERROR:", e)


if __name__ == "__main__":
    main()
