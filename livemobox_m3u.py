import os
import requests
from datetime import datetime, timedelta, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# =====================================================
# CONFIG
# =====================================================
JSON_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/matches.json"
OUTPUT_M3U = "dist/livemobox.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android IPTV)"
}

# WIB (UTC+7)
WIB = timezone(timedelta(hours=7))
UPCOMING_URL = "about:blank"

# Thumbnail
THUMB_DIR = "thumbs"
THUMB_W, THUMB_H = 512, 288   # 16:9 IPTV safe

# Logo layout
LOGO_TARGET_HEIGHT = 120
GAP = 20

# Durasi pertandingan
MATCH_DURATION_MAP = {
    "NBA": timedelta(hours=3),
}
DEFAULT_DURATION = timedelta(hours=2)

# =====================================================
# HELPERS
# =====================================================
def is_m3u8(url):
    return isinstance(url, str) and ".m3u8" in url.lower()

def fetch_json(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def parse_wib_datetime(date_str, time_str):
    dt = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
    return dt.replace(tzinfo=WIB)

# =====================================================
# IMAGE BUILD (IPTV SAFE)
# =====================================================
def build_gradient_bg():
    img = Image.new("RGB", (THUMB_W, THUMB_H), "#111111")
    draw = ImageDraw.Draw(img)

    left = (30, 40, 90)
    right = (120, 30, 60)

    for x in range(THUMB_W):
        t = x / THUMB_W
        r = int(left[0] * (1 - t) + right[0] * t)
        g = int(left[1] * (1 - t) + right[1] * t)
        b = int(left[2] * (1 - t) + right[2] * t)
        draw.line([(x, 0), (x, THUMB_H)], fill=(r, g, b))

    return img

def fetch_logo(url):
    try:
        if not url:
            raise Exception("no logo")

        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()

        img = Image.open(BytesIO(r.content)).convert("RGB")

        w, h = img.size
        scale = LOGO_TARGET_HEIGHT / h
        img = img.resize((int(w * scale), LOGO_TARGET_HEIGHT), Image.LANCZOS)

        return img
    except Exception:
        # fallback blank logo
        return Image.new("RGB", (LOGO_TARGET_HEIGHT, LOGO_TARGET_HEIGHT), "#333333")

def build_match_thumb(home_url, away_url, filename):
    os.makedirs(THUMB_DIR, exist_ok=True)
    path = os.path.join(THUMB_DIR, filename)

    if os.path.exists(path):
        return path

    bg = build_gradient_bg()
    draw = ImageDraw.Draw(bg)

    home = fetch_logo(home_url)
    away = fetch_logo(away_url)

    cx, cy = THUMB_W // 2, THUMB_H // 2

    # Paste logos (RAPAT)
    bg.paste(home, (cx - GAP - home.width, cy - home.height // 2))
    bg.paste(away, (cx + GAP, cy - away.height // 2))

    # VS text
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
        draw.text((cx+dx, cy+dy), "VS", fill=(0,0,0), anchor="mm")
    draw.text((cx, cy), "VS", fill=(255,255,255), anchor="mm")

    # SAVE AS JPG (IPTV SAFE)
    bg.save(path, "JPEG", quality=92, subsampling=0)
    return path

# =====================================================
# MAIN
# =====================================================
def main():
    data = fetch_json(JSON_URL)
    now_wib = datetime.now(WIB)
    cache_bust = int(now_wib.timestamp())

    m3u = ["#EXTM3U"]

    for item in data:
        title = item.get("match_title_from_api", "Unknown Match")
        competition = item.get("competition", "SPORT")
        match_id = item.get("match_id", "0")
        date_wib = item.get("date", "")
        time_wib = item.get("time", "")

        home_logo = item.get("team1", {}).get("logo_url")
        away_logo = item.get("team2", {}).get("logo_url")

        kickoff = parse_wib_datetime(date_wib, time_wib)
        duration = MATCH_DURATION_MAP.get(competition, DEFAULT_DURATION)
        end_time = kickoff + duration

        links = item.get("links", [])
        m3u8_links = [u for u in links if is_m3u8(u)]

        if m3u8_links:
            if now_wib < kickoff:
                status = "[UPCOMING]"
                urls = [UPCOMING_URL]
            elif now_wib <= end_time:
                status = "[LIVE]"
                urls = m3u8_links
            else:
                status = "[END]"
                urls = m3u8_links
        else:
            status = "[UPCOMING]"
            urls = [UPCOMING_URL]

        thumb_name = f"{match_id}.jpg"
        thumb_path = build_match_thumb(home_logo, away_logo, thumb_name)

        thumb_url = (
            "https://raw.githubusercontent.com/evafourbasri-afk/"
            "streamedsu-autoscraper/main/"
            + thumb_path.replace("\\", "/")
            + f"?v={cache_bust}"
        )

        channel_name = f"{status} {title} | {date_wib} {time_wib} WIB"

        for url in urls:
            m3u.append(
                f'#EXTINF:-1 tvg-id="{match_id}" '
                f'tvg-logo="{thumb_url}" '
                f'group-title="{competition}",{channel_name}'
            )
            m3u.append(url)

    os.makedirs("dist", exist_ok=True)
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("✅ FINAL: livemobox.m3u + JPG thumbnails generated")

# =====================================================
if __name__ == "__main__":
    main()
