import requests
from PIL import Image, ImageDraw
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo
import os

# ================================
# CONFIG
# ================================
API_URL = "https://pixelsport.tv/backend/liveTV/events"
OUTPUT_M3U = "NewPixel.m3u8"
THUMB_DIR = "thumbs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Referer": "https://pixelsport.tv/",
    "Origin": "https://pixelsport.tv",
    "Accept": "*/*",
}

EVENT_LOGO_MAP = {
    "NFL": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NFL.png",
    "NHL": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NHL.png",
    "NBA": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NBA.png",
    "MLB": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/MLB.png",
}

THUMB_W, THUMB_H = 512, 288
LOGO_SIZE = 130
EVENT_SIZE = 85


# ================================
# GRADIENT BUILDER
# ================================
def build_gradient():
    img = Image.new("RGB", (THUMB_W, THUMB_H), "#000")
    draw = ImageDraw.Draw(img)

    colors = [
        (20, 30, 80),     # Dark Blue
        (60, 20, 90),     # Deep Purple
        (120, 30, 60)     # Dark Red Pink
    ]

    for x in range(THUMB_W):
        t = x / THUMB_W
        if t < 0.5:
            r = int(colors[0][0] * (1 - t * 2) + colors[1][0] * (t * 2))
            g = int(colors[0][1] * (1 - t * 2) + colors[1][1] * (t * 2))
            b = int(colors[0][2] * (1 - t * 2) + colors[1][2] * (t * 2))
        else:
            t2 = (t - 0.5) * 2
            r = int(colors[1][0] * (1 - t2) + colors[2][0] * t2)
            g = int(colors[1][1] * (1 - t2) + colors[2][1] * t2)
            b = int(colors[1][2] * (1 - t2) + colors[2][2] * t2)

        draw.line([(x, 0), (x, THUMB_H)], fill=(r, g, b))

    return img


# ================================
# IMAGE DOWNLOADER + RESIZER
# ================================
def fetch_logo(url, size):
    try:
        r = requests.get(url, timeout=10)
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        img.thumbnail((size, size), Image.LANCZOS)
        return img
    except:
        return None


# ================================
# BUILD THUMB
# ================================
def build_thumb(home_url, away_url, event_logo, filename):
    bg = build_gradient()

    home = fetch_logo(home_url, LOGO_SIZE)
    away = fetch_logo(away_url, LOGO_SIZE)
    evl  = fetch_logo(event_logo, EVENT_SIZE)

    if home:
        bg.paste(home, (100, int(THUMB_H/2 - home.height/2)), home)
    if away:
        bg.paste(away, (THUMB_W - 100 - away.width, int(THUMB_H/2 - away.height/2)), away)
    if evl:
        bg.paste(evl, (int(THUMB_W/2 - evl.width/2), int(THUMB_H/2 - evl.height/2)), evl)

    bg.save(f"{THUMB_DIR}/{filename}", "PNG")
    return f"{THUMB_DIR}/{filename}"


# ================================
# MAIN SCRAPER
# ================================
def scrape_pixel():
    os.makedirs(THUMB_DIR, exist_ok=True)

    events = requests.get(API_URL, headers=HEADERS, timeout=10).json().get("events", [])

    lines = ["#EXTM3U"]

    for ev in events:
        title = ev.get("match_name", "Unknown")

        home_logo = ev.get("competitors1_logo")
        away_logo = ev.get("competitors2_logo")

        league = ev.get("channel", {}).get("TVCategory", {}).get("name", "").upper()
        event_logo = EVENT_LOGO_MAP.get(league, EVENT_LOGO_MAP["NFL"])

        # ======================
        # WIB TIME
        # ======================
        ts = ev.get("start_time")
        if ts:
            dt = datetime.fromtimestamp(int(ts)/1000, tz=ZoneInfo("UTC"))
            wib = dt.astimezone(ZoneInfo("Asia/Jakarta"))
            title += f" | {wib.strftime('%d %b %Y %H:%M WIB')}"

        # ======================
        # THUMBNAIL GENERATE
        # ======================
        fname = f"{league}_{ev.get('id','0')}.png"
        thumb_url = build_thumb(home_logo, away_logo, event_logo, fname)

        # ======================
        # STREAM LINKS
        # ======================
        links = [
            ev.get("channel", {}).get("server1URL"),
            ev.get("channel", {}).get("server2URL"),
            ev.get("channel", {}).get("server3URL"),
        ]

        for link in links:
            if not link or link == "null":
                continue

            lines.append(
                f'#EXTINF:-1 tvg-logo="https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/{thumb_url}" '
                f'group-title="PixelSport - {league}",{title}'
            )
            lines.append(f"#EXTVLCOPT:http-user-agent={HEADERS['User-Agent']}")
            lines.append(f"#EXTVLCOPT:http-referrer={HEADERS['Referer']}")
            lines.append(f"#EXTVLCOPT:http-origin={HEADERS['Origin']}")
            lines.append(link)

    open(OUTPUT_M3U, "w", encoding="utf-8").write("\n".join(lines))
    print(f"[OK] Saved → {OUTPUT_M3U}")


scrape_pixel()
