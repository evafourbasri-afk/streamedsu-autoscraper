import json
import urllib.request
import requests
from urllib.error import URLError, HTTPError
from PIL import Image, ImageDraw
import io
import os
from datetime import datetime, timedelta, timezone

# ======================================================
# CONFIG
# ======================================================

BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"

OUTPUT_FILE = "NewPixel.m3u8"

RAW_BASE = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main"

THUMB_DIR = "thumbnails"

VLC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
VLC_REFERER = f"{BASE}/"
VLC_ICY = "1"

DEFAULT_LOGO = "https://pixelsport.tv/static/media/PixelSportLogo.1182b5f687c239810f6d.png"


# ======================================================
# CATEGORY MAPPING (OFFICIAL PIXELSPORT)
# ======================================================
# PixelSport Categories:
# Baseball → MLB
# Basketball → NBA
# American Football → NFL
# Ice Hockey → NHL

LEAGUE_MAP = {
    "mlb": "MLB",
    "baseball": "MLB",

    "nba": "NBA",
    "basket": "NBA",
    "basketball": "NBA",

    "nfl": "NFL",
    "football": "NFL",
    "american football": "NFL",

    "nhl": "NHL",
    "hockey": "NHL",
    "ice hockey": "NHL",
}


# ======================================================
# PNG LOGOS FOR LEAGUES (COMPATIBLE WITH PILLOW)
# ======================================================
LEAGUE_LOGOS = {
    "NBA": "https://i.imgur.com/3R8H0kT.png",
    "NFL": "https://i.imgur.com/AxHwU1l.png",
    "MLB": "https://i.imgur.com/H3cG9eA.png",
    "NHL": "https://i.imgur.com/q4LX0SK.png",
}


# ======================================================
# WIB TIME CONVERTER
# ======================================================
def to_wib(timestamp_ms):
    try:
        ts = int(timestamp_ms) / 1000
        dt_utc = datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc)
        dt_wib = dt_utc + timedelta(hours=7)
        return dt_wib.strftime("%d %b %Y %H:%M WIB")
    except:
        return ""


# ======================================================
# CATEGORY → LEAGUE GROUP
# ======================================================
def get_league_group(raw_name):
    if not raw_name:
        return "PixelSport - Other"

    name = raw_name.lower()
    for key, league in LEAGUE_MAP.items():
        if key in name:
            return f"PixelSport - {league}"

    return "PixelSport - Other"


def get_league_logo(group_title):
    for key, url in LEAGUE_LOGOS.items():
        if key.lower() in group_title.lower():
            return url
    return None


# ======================================================
# GRADIENT COLORS BY LEAGUE
# ======================================================
def get_gradient_colors(group_title):
    gt = group_title.lower()

    if "nba" in gt:
        return (20, 20, 80), (0, 100, 220)
    if "nfl" in gt:
        return (10, 40, 80), (120, 0, 0)
    if "mlb" in gt:
        return (0, 40, 120), (140, 0, 0)
    if "nhl" in gt:
        return (30, 30, 30), (90, 90, 90)

    return (30, 30, 30), (80, 80, 80)


# ======================================================
# FETCH JSON
# ======================================================
def fetch_json(url):
    headers = {
        "User-Agent": VLC_USER_AGENT,
        "Referer": VLC_REFERER,
        "Accept": "*/*",
        "Connection": "close",
        "Icy-MetaData": VLC_ICY
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ======================================================
# THUMBNAIL GENERATOR (FINAL FIX)
# ======================================================
def generate_match_logo(home_url, away_url, group_title, output_path):
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        img1 = Image.open(io.BytesIO(requests.get(home_url, timeout=10).content)).convert("RGBA")
        img2 = Image.open(io.BytesIO(requests.get(away_url, timeout=10).content)).convert("RGBA")

        league_logo_url = get_league_logo(group_title)
        league_logo = None
        if league_logo_url:
            try:
                league_logo = Image.open(io.BytesIO(requests.get(league_logo_url, timeout=10).content)).convert("RGBA")
            except:
                league_logo = None

        width, height = 1280, 720
        bg = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(bg)

        col1, col2 = get_gradient_colors(group_title)

        for x in range(width):
            ratio = x / width
            r = int(col1[0] + (col2[0] - col1[0]) * ratio)
            g = int(col1[1] + (col2[1] - col1[1]) * ratio)
            b = int(col1[2] + (col2[2] - col1[2]) * ratio)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))

        def scale(img):
            ratio = 360 / img.size[1]
            return img.resize((int(img.size[0] * ratio), 360), Image.LANCZOS)

        img1 = scale(img1)
        img2 = scale(img2)

        total_w = img1.width + img2.width + 120
        start_x = (width - total_w) // 2
        y = (height - 360) // 2

        bg.paste(img1, (start_x, y), img1)
        bg.paste(img2, (start_x + img1.width + 120, y), img2)

        if league_logo:
            league_logo = league_logo.resize((200, 200), Image.LANCZOS)
            cx = (width - league_logo.width) // 2
            cy = (height - league_logo.height) // 2
            bg.paste(league_logo, (cx, cy), league_logo)

        bg.save(output_path, "PNG")
        return True

    except Exception as e:
        print("Thumbnail error:", e)
        return False


# ======================================================
# PARSE LINKS
# ======================================================
def collect_links(obj):
    links = []
    for i in range(1, 4):
        url = obj.get(f"server{i}URL")
        if url and url.lower() != "null":
            links.append(url)
    return links


# ======================================================
# BUILD M3U (WIB VERSION)
# ======================================================
def build_m3u(events, sliders):
    out = ["#EXTM3U"]

    for ev in events:

        # TITLE + WIB TIME
        raw_title = ev.get("match_name", "Unknown Event").strip()

        timestamp = (
            ev.get("date")
            or ev.get("time")
            or ev.get("startTimestamp")
            or ev.get("start_time")
            or ev.get("startDate")
            or 0
        )
        wib_time = to_wib(timestamp)

        title = f"{raw_title} - {wib_time}"

        # LOGO HOME AWAY
        home = ev.get("competitors1_logo") or DEFAULT_LOGO
        away = ev.get("competitors2_logo") or DEFAULT_LOGO

        # LEAGUE GROUP
        raw_cat = ev.get("channel", {}).get("TVCategory", {}).get("name", "")
        group = get_league_group(raw_cat)

        # THUMB PATH
        safe = raw_title.replace(" ", "_").replace("/", "_").replace(":", "_")
        thumb_rel = f"{THUMB_DIR}/{safe}.png"

        if generate_match_logo(home, away, group, thumb_rel):
            tvg_logo = f"{RAW_BASE}/{thumb_rel}"
        else:
            tvg_logo = home

        links = collect_links(ev.get("channel", {}))
        for link in links:
            out.append(f'#EXTINF:-1 tvg-logo="{tvg_logo}" group-title="{group}",{title}')
            out.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            out.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            out.append(link)

    return "\n".join(out)


# ======================================================
# MAIN EXECUTION
# ======================================================
def main():
    try:
        os.makedirs(THUMB_DIR, exist_ok=True)

        print("[*] Fetching events...")
        events = fetch_json(API_EVENTS).get("events", [])

        print("[*] Fetching sliders...")
        sliders = fetch_json(API_SLIDERS).get("data", [])

        m3u = build_m3u(events, sliders)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(m3u)

        print("[✓] Saved:", OUTPUT_FILE)
        print("[✓] Events:", len(events))
        print("[✓] Sliders:", len(sliders))

    except Exception as e:
        print("[ERROR]", e)


if __name__ == "__main__":
    main()
