import os
import requests
from datetime import datetime, timedelta, timezone
from io import BytesIO
from PIL import Image, ImageDraw

# =====================================================
# CONFIG
# =====================================================
JSON_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/matches.json"
OUTPUT_M3U = "livemobox.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android; IPTV)"
}

# WIB = UTC+7 (tanpa pytz)
WIB = timezone(timedelta(hours=7))

MATCH_DURATION = timedelta(hours=2)
UPCOMING_URL = "about:blank"

# Thumbnail config
THUMB_DIR = "thumbs"
THUMB_W, THUMB_H = 512, 288
LOGO_SIZE = 130
GAP = 28  # jarak logo ke tulisan VS

# =====================================================
# BASIC HELPERS
# =====================================================
def is_m3u8(url: str) -> bool:
    return isinstance(url, str) and ".m3u8" in url.lower()

def fetch_json(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def parse_wib_datetime(date_str, time_str):
    dt = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
    return dt.replace(tzinfo=WIB)

# =====================================================
# IMAGE HELPERS
# =====================================================
def build_gradient():
    img = Image.new("RGB", (THUMB_W, THUMB_H), "#000000")
    draw = ImageDraw.Draw(img)

    colors = [
        (20, 30, 80),
        (60, 20, 90),
        (120, 30, 60),
    ]

    for x in range(THUMB_W):
        t = x / THUMB_W
        if t < 0.5:
            t2 = t * 2
            r = int(colors[0][0] * (1 - t2) + colors[1][0] * t2)
            g = int(colors[0][1] * (1 - t2) + colors[1][1] * t2)
            b = int(colors[0][2] * (1 - t2) + colors[1][2] * t2)
        else:
            t2 = (t - 0.5) * 2
            r = int(colors[1][0] * (1 - t2) + colors[2][0] * t2)
            g = int(colors[1][1] * (1 - t2) + colors[2][1] * t2)
            b = int(colors[1][2] * (1 - t2) + colors[2][2] * t2)

        draw.line([(x, 0), (x, THUMB_H)], fill=(r, g, b))

    return img

def fetch_logo(url, size):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        img.thumbnail((size, size), Image.LANCZOS)
        return img
    except Exception:
        return None

def build_match_thumb(home_url, away_url, filename):
    os.makedirs(THUMB_DIR, exist_ok=True)
    bg = build_gradient()
    draw = ImageDraw.Draw(bg)

    home = fetch_logo(home_url, LOGO_SIZE)
    away = fetch_logo(away_url, LOGO_SIZE)

    center_x = THUMB_W // 2
    center_y = THUMB_H // 2

    # HOME (kiri)
    if home:
        x = center_x - GAP - home.width
        y = center_y - home.height // 2
        bg.paste(home, (x, y), home)

    # AWAY (kanan)
    if away:
        x = center_x + GAP
        y = center_y - away.height // 2
        bg.paste(away, (x, y), away)

    # Text "VS" di tengah
    vs_text = "VS"

    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
        draw.text(
            (center_x + dx, center_y + dy),
            vs_text,
            fill=(0, 0, 0),
            anchor="mm"
        )

    draw.text(
        (center_x, center_y),
        vs_text,
        fill=(255, 255, 255),
        anchor="mm"
    )

    path = os.path.join(THUMB_DIR, filename)
    bg.save(path, "PNG")
    return path

# =====================================================
# MAIN
# =====================================================
def main():
    data = fetch_json(JSON_URL)
    now_wib = datetime.now(WIB)

    m3u = ["#EXTM3U"]

    for item in data:
        title = item.get("match_title_from_api", "Unknown Match")
        competition = item.get("competition", "SPORT")
        match_id = item.get("match_id", "")
        date_wib = item.get("date", "")
        time_wib = item.get("time", "")

        home_logo = item.get("team1", {}).get("logo_url")
        away_logo = item.get("team2", {}).get("logo_url")

        kickoff = parse_wib_datetime(date_wib, time_wib)
        end_time = kickoff + MATCH_DURATION

        links = item.get("links", [])
        m3u8_links = [u for u in links if is_m3u8(u)]

        if now_wib > end_time:
            status = "[END]"
            urls = [UPCOMING_URL]
        elif now_wib >= kickoff and m3u8_links:
            status = "[LIVE]"
            urls = m3u8_links
        else:
            status = "[UPCOMING]"
            urls = [UPCOMING_URL]

        thumb_name = f"{match_id}.png"
        thumb_path = build_match_thumb(home_logo, away_logo, thumb_name)
        thumb_url = (
            "https://raw.githubusercontent.com/evafourbasri-afk/"
            "streamedsu-autoscraper/main/" + thumb_path.replace("\\", "/")
        )

        channel_name = f"{status} {title} | {date_wib} {time_wib} WIB"

        for url in urls:
            m3u.append(
                f'#EXTINF:-1 tvg-id="{match_id}" '
                f'tvg-logo="{thumb_url}" '
                f'group-title="{competition}",'
                f'{channel_name}'
            )
            m3u.append(url)

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print(f"✅ Generated {OUTPUT_M3U}")

# =====================================================
if __name__ == "__main__":
    main()
