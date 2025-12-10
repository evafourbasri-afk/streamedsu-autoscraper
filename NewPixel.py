import json
import urllib.request
import requests
from urllib.error import URLError, HTTPError
from PIL import Image, ImageDraw
import io
import os

# ==========================================
# CONFIG
# ==========================================

BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"

OUTPUT_FILE = "NewPixel.m3u8"

# base URL untuk akses PNG di repo GitHub kamu
RAW_BASE = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main"

THUMB_DIR = "thumbnails"

VLC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
VLC_REFERER = f"{BASE}/"
VLC_ICY = "1"

DEFAULT_LOGO = "https://pixelsport.tv/static/media/PixelSportLogo.1182b5f687c239810f6d.png"

LEAGUE_MAP = {
    "nba": "NBA",
    "basket": "NBA",
    "nfl": "NFL",
    "football": "NFL",
    "mlb": "MLB",
    "baseball": "MLB",
    "nhl": "NHL",
    "hockey": "NHL",
    "ufc": "UFC",
    "mma": "UFC",
    "boxing": "Boxing",
    "fight": "Boxing",
    "f1": "F1",
    "formula": "F1",
    "nascar": "Racing",
    "motor": "Racing",
    "epl": "EPL",
    "premier": "EPL",
    "england": "EPL",
    "laliga": "LaLiga",
    "spain": "LaLiga",
    "bundes": "Bundesliga",
    "german": "Bundesliga",
    "serie a": "Serie A",
    "italy": "Serie A",
    "ligue": "Ligue 1",
    "france": "Ligue 1",
    "mls": "MLS",
    "america": "MLS",
    "soccer": "Soccer",
    "futbol": "Soccer"
}


# ==========================================
# LEAGUE GROUP & GRADIENT COLORS
# ==========================================

def get_league_group(raw_name):
    if not raw_name:
        return "PixelSport - Other"
    name = raw_name.lower()
    for key, cat in LEAGUE_MAP.items():
        if key in name:
            return f"PixelSport - {cat}"
    return "PixelSport - Other"


def get_gradient_colors(group_title):
    gt = group_title.lower()
    # warna bisa kamu atur sendiri
    if "epl" in gt:
        return (200, 20, 0), (255, 180, 0)       # merah → oranye
    if "serie a" in gt:
        return (5, 40, 120), (0, 120, 255)       # biru tua → biru muda
    if "bundes" in gt:
        return (150, 0, 0), (60, 0, 0)           # merah tua → marun
    if "laliga" in gt:
        return (80, 0, 120), (220, 40, 60)       # ungu → merah
    if "nba" in gt:
        return (20, 20, 80), (0, 100, 220)       # biru gelap → biru
    if "nfl" in gt:
        return (10, 40, 80), (120, 0, 0)         # biru → merah
    if "mlb" in gt:
        return (10, 10, 50), (150, 0, 0)
    if "nhl" in gt:
        return (20, 20, 20), (120, 120, 120)
    if "ufc" in gt or "boxing" in gt:
        return (120, 0, 0), (10, 10, 10)
    # default
    return (20, 20, 20), (60, 60, 60)


# ==========================================
# FETCH JSON
# ==========================================

def fetch_json(url):
    headers = {
        "User-Agent": VLC_USER_AGENT,
        "Referer": VLC_REFERER,
        "Accept": "*/*",
        "Connection": "close",
        "Icy-MetaData": VLC_ICY
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ==========================================
# IMAGE: MERGE HOME & AWAY + GRADIENT
# ==========================================

def generate_match_logo(home_url, away_url, group_title, output_path):
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        r1 = requests.get(home_url, timeout=10)
        r2 = requests.get(away_url, timeout=10)

        img1 = Image.open(io.BytesIO(r1.content)).convert("RGBA")
        img2 = Image.open(io.BytesIO(r2.content)).convert("RGBA")

        width, height = 1280, 720
        bg = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(bg)

        start_color, end_color = get_gradient_colors(group_title)

        # horizontal gradient
        for x in range(width):
            ratio = x / width
            r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))

        # resize logo
        max_logo_h = 360
        def resize_keep_ratio(img):
            w, h = img.size
            ratio = max_logo_h / float(h)
            return img.resize((int(w * ratio), max_logo_h), Image.LANCZOS)

        img1 = resize_keep_ratio(img1)
        img2 = resize_keep_ratio(img2)

        # posisi kiri & kanan
        gap = 80
        total_w = img1.width + img2.width + gap
        start_x = (width - total_w) // 2
        y = (height - max_logo_h) // 2

        bg.paste(img1, (start_x, y), img1)
        bg.paste(img2, (start_x + img1.width + gap, y), img2)

        bg.save(output_path, "PNG")
        return True
    except Exception as e:
        print("Error generating match logo:", e)
        return False


# ==========================================
# UTIL
# ==========================================

def collect_links(obj):
    links = []
    for i in range(1, 4):
        url = obj.get(f"server{i}URL")
        if url and url.lower() != "null":
            links.append(url)
    return links


# ==========================================
# BUILD M3U
# ==========================================

def build_m3u(events, sliders):
    lines = ["#EXTM3U"]

    # EVENTS
    for ev in events:
        title = ev.get("match_name", "Unknown Event").strip()

        # logo home & away langsung dari JSON
        home_logo = ev.get("competitors1_logo") or DEFAULT_LOGO
        away_logo = ev.get("competitors2_logo") or DEFAULT_LOGO

        raw_cat = ev.get("channel", {}).get("TVCategory", {}).get("name", "")
        group_title = get_league_group(raw_cat)

        # generate file name aman
        safe_name = (
            title.replace(" ", "_")
            .replace("/", "_")
            .replace(":", "_")
            .replace("|", "_")
        )
        thumb_rel = f"{THUMB_DIR}/{safe_name}.png"
        thumb_path = os.path.join(thumb_rel)

        # buat gambar gabungan
        if home_logo and away_logo:
            ok = generate_match_logo(home_logo, away_logo, group_title, thumb_path)
            if ok:
                tvg_logo = f"{RAW_BASE}/{thumb_rel}"
            else:
                tvg_logo = home_logo
        else:
            tvg_logo = home_logo or away_logo or DEFAULT_LOGO

        links = collect_links(ev.get("channel", {}))
        if not links:
            continue

        for link in links:
            lines.append(
                f'#EXTINF:-1 tvg-logo="{tvg_logo}" group-title="{group_title}",{title}'
            )
            lines.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            lines.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            lines.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            lines.append(link)

    # SLIDERS (tetap pakai logo default)
    for ch in sliders:
        title = ch.get("title", "Live Channel")
        live = ch.get("liveTV", {})
        links = collect_links(live)
        if not links:
            continue

        for link in links:
            lines.append(
                f'#EXTINF:-1 tvg-logo="{DEFAULT_LOGO}" group-title="PixelSport - Live",{title}'
            )
            lines.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            lines.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            lines.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            lines.append(link)

    return "\n".join(lines)


# ==========================================
# MAIN
# ==========================================

def main():
    try:
        os.makedirs(THUMB_DIR, exist_ok=True)

        print("[*] Fetching events...")
        events = fetch_json(API_EVENTS).get("events", [])

        print("[*] Fetching sliders...")
        sliders = fetch_json(API_SLIDERS).get("data", [])

        playlist = build_m3u(events, sliders)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(playlist)

        print(f"[✓] Saved as {OUTPUT_FILE}")
        print(f"[✓] Events: {len(events)}, Sliders: {len(sliders)}")

    except Exception as e:
        print("[X] ERROR:", e)


if __name__ == "__main__":
    main()
