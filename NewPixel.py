import json
import urllib.request
import requests
from urllib.error import URLError, HTTPError
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from io import BytesIO
import os

# =========================
# CONFIG
# =========================

BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"

OUTPUT_FILE = "NewPixel.m3u8"

# GitHub RAW event logos
RAW = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos"

LEAGUE_LOGOS = {
    "NBA": f"{RAW}/NBA.png",
    "NFL": f"{RAW}/NFL.png",
    "MLB": f"{RAW}/MLB.png",
    "NHL": f"{RAW}/NHL.png",
}

DEFAULT_LOGO = f"{RAW}/NBA.png"  # fallback
THUMB_FOLDER = "thumbs"
os.makedirs(THUMB_FOLDER, exist_ok=True)

VLC_USER_AGENT = "Mozilla/5.0"
VLC_REFERER = BASE
VLC_ICY = "1"


# =========================
# HELPERS
# =========================

def fetch_json(url):
    headers = {"User-Agent": VLC_USER_AGENT, "Referer": VLC_REFERER}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_image(url):
    try:
        r = requests.get(url, timeout=10)
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except:
        return None


def merge_logos(logo1_url, event_logo_url, logo2_url, filename):
    """Gabungkan logo home + event + away"""
    img1 = load_image(logo1_url)
    img2 = load_image(logo2_url)
    evt = load_image(event_logo_url)

    if img1 is None and img2 is None:
        return None

    if img1 is None:
        img1 = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    if img2 is None:
        img2 = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    if evt is None:
        evt = Image.new("RGBA", (180, 180), (255, 255, 255, 0))

    img1 = img1.resize((256, 256))
    img2 = img2.resize((256, 256))
    evt = evt.resize((180, 180))

    W = 256 * 2 + 180
    H = 256
    canvas = Image.new("RGBA", (W, H), (10, 10, 10, 255))

    # Paste left, middle, right
    canvas.paste(img1, (0, 0), img1)
    canvas.paste(evt, (256, 38), evt)
    canvas.paste(img2, (256 + 180, 0), img2)

    path = f"{THUMB_FOLDER}/{filename}.png"
    canvas.save(path)
    return path


def detect_league(name):
    if not name:
        return "MLB"     # fallback
    name = name.lower()
    if "basket" in name or "nba" in name:
        return "NBA"
    if "football" in name or "nfl" in name:
        return "NFL"
    if "hockey" in name or "nhl" in name:
        return "NHL"
    if "baseball" in name or "mlb" in name:
        return "MLB"
    return "MLB"


def to_wib(date_str):
    try:
        # contoh format: "2026-01-15T02:30:00.000Z"
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        wib = dt + timedelta(hours=7)
        return wib.strftime("%d/%m/%Y %H:%M WIB")
    except:
        return ""


def collect_links(ch):
    links = []
    for i in range(1, 4):
        url = ch.get(f"server{i}URL")
        if url and url.lower() != "null":
            links.append(url)
    return links


# =========================
# BUILDING M3U
# =========================

def build_m3u(events, sliders):
    out = ["#EXTM3U"]

    for ev in events:

        title = ev.get("match_name", "Unknown Match").strip()
        time_raw = ev.get("startTime") or ""
        time_wib = to_wib(time_raw)

        t1 = ev.get("competitors1_name")
        t2 = ev.get("competitors2_name")

        logo1 = ev.get("competitors1_logo")
        logo2 = ev.get("competitors2_logo")

        # Detect league by pixelsport category
        league_raw = ev.get("channel", {}).get("TVCategory", {}).get("name", "")
        league = detect_league(league_raw)
        event_logo_url = LEAGUE_LOGOS.get(league, DEFAULT_LOGO)

        # Build thumbnail file
        fname = f"{t1}_{t2}".replace(" ", "_")
        thumb_path = merge_logos(logo1, event_logo_url, logo2, fname)
        thumb_raw = f"https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/{thumb_path}"

        links = collect_links(ev.get("channel", {}))
        if not links:
            continue

        final_title = f"{title} | {time_wib}"

        for link in links:
            out.append(f'#EXTINF:-1 tvg-logo="{thumb_raw}" group-title="PixelSport - {league}",{final_title}')
            out.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            out.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            out.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            out.append(link)

    return "\n".join(out)


# =========================
# MAIN
# =========================

def main():
    try:
        print("[*] Fetching events...")
        events = fetch_json(API_EVENTS).get("events", [])

        print("[*] Building M3U...")
        m3u = build_m3u(events, [])

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(m3u)

        print(f"[✓] Saved as {OUTPUT_FILE}")
        print(f"[✓] Events:", len(events))

    except Exception as e:
        print("[X] ERROR:", e)


if __name__ == "__main__":
    main()
