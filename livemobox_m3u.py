import os
import requests
from io import BytesIO
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw

# =====================================================
# CONFIG
# =====================================================
JSON_URL = "https://ogietv.biz.id/m3u/matches.json"
OUTPUT_M3U = "dist/livemobox.m3u"

LOGO_DIR = "logos"
CANVAS_W, CANVAS_H = 400, 180
LOGO_H = 120
GAP = 20

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android IPTV)"
}

WIB = timezone(timedelta(hours=7))
UPCOMING_URL = "about:blank"

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

def fetch_logo(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        w, h = img.size
        scale = LOGO_H / h
        return img.resize((int(w * scale), LOGO_H), Image.LANCZOS)
    except Exception:
        return None

def build_vs_logo(home_url, away_url, out_path):
    os.makedirs(LOGO_DIR, exist_ok=True)

    if os.path.exists(out_path):
        return out_path

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0,0,0,0))
    draw = ImageDraw.Draw(canvas)

    home = fetch_logo(home_url)
    away = fetch_logo(away_url)

    cx, cy = CANVAS_W // 2, CANVAS_H // 2

    if home:
        canvas.paste(home, (cx - GAP - home.width, cy - home.height // 2), home)
    if away:
        canvas.paste(away, (cx + GAP, cy - away.height // 2), away)

    draw.text((cx, cy), "VS", fill=(255,255,255,255), anchor="mm")

    canvas.save(out_path, "PNG")
    return out_path

# =====================================================
# MAIN
# =====================================================
def main():
    data = fetch_json(JSON_URL)
    now = datetime.now(WIB)

    m3u = ["#EXTM3U"]

    for item in data:
        match_id = item.get("match_id", "0")
        title = item.get("match_title_from_api", "Match")
        competition = item.get("competition", "SPORT")
        date_wib = item.get("date", "")
        time_wib = item.get("time", "")

        home_logo = item.get("team1", {}).get("logo_url")
        away_logo = item.get("team2", {}).get("logo_url")

        kickoff = parse_wib_datetime(date_wib, time_wib)
        duration = MATCH_DURATION_MAP.get(competition, DEFAULT_DURATION)
        end_time = kickoff + duration

        links = item.get("links", [])
        m3u8_links = [u for u in links if is_m3u8(u)]

        if now < kickoff:
            status, urls = "[UPCOMING]", [UPCOMING_URL]
        elif now <= end_time:
            status, urls = "[LIVE]", m3u8_links
        else:
            status, urls = "[END]", m3u8_links

        logo_path = build_vs_logo(
            home_logo,
            away_logo,
            f"{LOGO_DIR}/{match_id}.png"
        )

        logo_url = (
            "https://raw.githubusercontent.com/evafourbasri-afk/"
            "streamedsu-autoscraper/main/"
            + logo_path
        )

        channel_name = f"{status} {title} | {date_wib} {time_wib} WIB"

        for url in urls:
            m3u.append(
                f'#EXTINF:-1 tvg-id="{match_id}" '
                f'tvg-logo="{logo_url}" '
                f'group-title="{competition}",{channel_name}'
            )
            m3u.append(url)

    os.makedirs("dist", exist_ok=True)
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("✅ FINAL: Home vs Away transparent logos generated")

if __name__ == "__main__":
    main()
