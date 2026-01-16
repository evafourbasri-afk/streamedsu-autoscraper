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

# WIB (UTC+7)
WIB = timezone(timedelta(hours=7))

UPCOMING_URL = "about:blank"

# Thumbnail
THUMB_DIR = "thumbs"
THUMB_W, THUMB_H = 512, 288

# Logo visual
LOGO_TARGET_HEIGHT = 120
LOGO_MIN_WIDTH = 110
GAP = 28

# Durasi per kompetisi (NBA = 3 jam)
MATCH_DURATION_MAP = {
    "NBA": timedelta(hours=3),
}
DEFAULT_DURATION = timedelta(hours=2)

# =====================================================
# HELPERS
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
# IMAGE
# =====================================================
def build_gradient():
    img = Image.new("RGB", (THUMB_W, THUMB_H), "#000000")
    draw = ImageDraw.Draw(img)

    colors = [(20, 30, 80), (60, 20, 90), (120, 30, 60)]

    for x in range(THUMB_W):
        t = x / THUMB_W
        if t < 0.5:
            t2 = t * 2
            c1, c2 = colors[0], colors[1]
        else:
            t2 = (t - 0.5) * 2
            c1, c2 = colors[1], colors[2]

        r = int(c1[0] * (1 - t2) + c2[0] * t2)
        g = int(c1[1] * (1 - t2) + c2[1] * t2)
        b = int(c1[2] * (1 - t2) + c2[2] * t2)

        draw.line([(x, 0), (x, THUMB_H)], fill=(r, g, b))

    return img

def trim_transparency(img):
    if img.mode != "RGBA":
        return img
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img

def fetch_logo(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")

        img = trim_transparency(img)

        # scale by HEIGHT
        w, h = img.size
        scale = LOGO_TARGET_HEIGHT / h
        new_w = int(w * scale)
        new_h = LOGO_TARGET_HEIGHT
        img = img.resize((new_w, new_h), Image.LANCZOS)

        # force min width (fix NBA logo ramping)
        if new_w < LOGO_MIN_WIDTH:
            scale = LOGO_MIN_WIDTH / new_w
            img = img.resize((LOGO_MIN_WIDTH, int(new_h * scale)), Image.LANCZOS)

        return img
    except Exception:
        return None

def build_match_thumb(home_url, away_url, filename):
    os.makedirs(THUMB_DIR, exist_ok=True)
    path = os.path.join(THUMB_DIR, filename)

    # STABIL: kalau sudah ada, tidak rebuild (hemat CI + tidak bikin flicker)
    if os.path.exists(path):
        return path

    bg = build_gradient()
    draw = ImageDraw.Draw(bg)

    home = fetch_logo(home_url)
    away = fetch_logo(away_url)

    cx, cy = THUMB_W // 2, THUMB_H // 2

    if home:
        bg.paste(home, (cx - GAP - home.width, cy - home.height // 2), home)
    if away:
        bg.paste(away, (cx + GAP, cy - away.height // 2), away)

    # VS text
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        draw.text((cx + dx, cy + dy), "VS", fill=(0, 0, 0), anchor="mm")
    draw.text((cx, cy), "VS", fill=(255, 255, 255), anchor="mm")

    bg.save(path, "PNG")
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

        # Durasi per kompetisi (NBA 3 jam)
        duration = MATCH_DURATION_MAP.get(competition, DEFAULT_DURATION)
        end_time = kickoff + duration

        links = item.get("links", [])
        m3u8_links = [u for u in links if is_m3u8(u)]

        # ============================
        # STATUS LOGIC (ANTI BLANK)
        # ============================
        if m3u8_links:
            if now_wib < kickoff:
                status = "[UPCOMING]"
                urls = [UPCOMING_URL]
            elif now_wib <= end_time:
                status = "[LIVE]"
                urls = m3u8_links
            else:
                status = "[END]"
                urls = m3u8_links  # 🔥 tetap pakai link kalau masih ada
        else:
            status = "[UPCOMING]"
            urls = [UPCOMING_URL]

        # Thumbnail (statis)
        thumb_name = f"{match_id}.png"
        thumb_path = build_match_thumb(home_logo, away_logo, thumb_name)

        # Cache bust query only (stabil untuk launcher)
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
                f'group-title="{competition}",'
                f'{channel_name}'
            )
            m3u.append(url)

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("✅ Generated livemobox.m3u (FINAL STABLE v2)")

# =====================================================
if __name__ == "__main__":
    main()
