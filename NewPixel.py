import json
import urllib.request
import requests
from urllib.error import URLError, HTTPError
from PIL import Image, ImageDraw
import io
import os

# ==============================================
# CONFIG
# ==============================================

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

# ==============================================
# LEAGUE MAPPING
# ==============================================

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
    "bundes": "Bundesliga",
    "serie a": "Serie A",
    "ligue": "Ligue 1",
    "mls": "MLS",
    "soccer": "Soccer",
    "futbol": "Soccer"
}

# ==============================================
# LEAGUE LOGO (TENGAH)
# ==============================================

LEAGUE_LOGOS = {
    "NBA": "https://upload.wikimedia.org/wikipedia/en/0/03/NBA_logo.svg",
    "NFL": "https://upload.wikimedia.org/wikipedia/en/a/a0/National_Football_League_logo.svg",
    "MLB": "https://upload.wikimedia.org/wikipedia/en/thumb/6/6d/Major_League_Baseball_logo.svg/320px-Major_League_Baseball_logo.svg.png",
    "NHL": "https://upload.wikimedia.org/wikipedia/en/3/3a/05_NHL_Shield.svg",
    "EPL": "https://upload.wikimedia.org/wikipedia/en/f/f2/Premier_League_Logo.svg",
    "Serie A": "https://upload.wikimedia.org/wikipedia/en/e/e1/Serie_A_logo_%282019%29.svg",
    "Bundesliga": "https://upload.wikimedia.org/wikipedia/en/d/df/Bundesliga_logo_%282017%29.svg",
    "LaLiga": "https://upload.wikimedia.org/wikipedia/en/6/6e/LaLiga_logo_2023.svg",
    "Ligue 1": "https://upload.wikimedia.org/wikipedia/en/c/cf/Ligue1_logo.svg",
    "MLS": "https://upload.wikimedia.org/wikipedia/commons/5/5e/MLS_crest_logo_RGB.svg",
    "UFC": "https://upload.wikimedia.org/wikipedia/commons/0/0d/UFC_Logo.svg",
    "Boxing": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Boxing_gloves_icon.svg/240px-Boxing_gloves_icon.svg.png",
}


# ==============================================
# FUNCTIONS
# ==============================================

def get_league_group(raw_name):
    if not raw_name:
        return "PixelSport - Other"
    name = raw_name.lower()
    for key, cat in LEAGUE_MAP.items():
        if key in name:
            return f"PixelSport - {cat}"
    return "PixelSport - Other"


def get_league_logo(group_title):
    for key, url in LEAGUE_LOGOS.items():
        if key.lower() in group_title.lower():
            return url
    return None


def get_gradient_colors(group_title):
    gt = group_title.lower()

    if "epl" in gt:
        return (200, 20, 0), (255, 160, 0)
    if "serie a" in gt:
        return (10, 40, 160), (0, 120, 255)
    if "bundes" in gt:
        return (150, 0, 0), (60, 0, 0)
    if "laliga" in gt:
        return (80, 0, 120), (200, 40, 60)
    if "nba" in gt:
        return (20, 20, 80), (0, 100, 220)
    if "nfl" in gt:
        return (10, 40, 80), (120, 0, 0)
    if "mlb" in gt:
        return (0, 40, 120), (140, 0, 0)
    if "nhl" in gt:
        return (30, 30, 30), (90, 90, 90)
    if "ufc" in gt or "boxing" in gt:
        return (120, 0, 0), (20, 20, 20)

    return (30, 30, 30), (80, 80, 80)


# ==============================================
# FETCH JSON
# ==============================================

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


# ==============================================
# GENERATE THUMBNAIL
# ==============================================

def generate_match_logo(home_url, away_url, group_title, output_path):
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        r1 = requests.get(home_url, timeout=10)
        r2 = requests.get(away_url, timeout=10)

        img1 = Image.open(io.BytesIO(r1.content)).convert("RGBA")
        img2 = Image.open(io.BytesIO(r2.content)).convert("RGBA")

        league_logo_url = get_league_logo(group_title)
        league_logo = None

        if league_logo_url:
            try:
                rl = requests.get(league_logo_url, timeout=10)
                league_logo = Image.open(io.BytesIO(rl.content)).convert("RGBA")
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

        max_h = 360

        def resize_logo(img):
            w, h = img.size
            ratio = max_h / h
            return img.resize((int(w * ratio), max_h), Image.LANCZOS)

        img1 = resize_logo(img1)
        img2 = resize_logo(img2)

        spacing = 120
        total_w = img1.width + img2.width + spacing
        start_x = (width - total_w) // 2
        y = (height - max_h) // 2

        bg.paste(img1, (start_x, y), img1)
        bg.paste(img2, (start_x + img1.width + spacing, y), img2)

        if league_logo:
            league_logo = league_logo.resize((200, 200), Image.LANCZOS)
            lx = (width - league_logo.width) // 2
            ly = (height - league_logo.height) // 2
            bg.paste(league_logo, (lx, ly), league_logo)

        bg.save(output_path, "PNG")
        return True

    except Exception as e:
        print("Error merging images:", e)
        return False


# ==============================================
# BUILD M3U
# ==============================================

def collect_links(obj):
    links = []
    for i in range(1, 4):
        u = obj.get(f"server{i}URL")
        if u and u.lower() != "null":
            links.append(u)
    return links


def build_m3u(events, sliders):
    out = ["#EXTM3U"]

    for ev in events:
        title = ev.get("match_name", "Unknown Event").strip()

        home = ev.get("competitors1_logo") or DEFAULT_LOGO
        away = ev.get("competitors2_logo") or DEFAULT_LOGO

        raw_cat = ev.get("channel", {}).get("TVCategory", {}).get("name", "")
        group = get_league_group(raw_cat)

        safe = (
            title.replace(" ", "_")
            .replace("/", "_")
            .replace(":", "_")
            .replace("|", "_")
        )
        thumb_rel = f"{THUMB_DIR}/{safe}.png"

        if generate_match_logo(home, away, group, thumb_rel):
            tvg_logo = f"{RAW_BASE}/{thumb_rel}"
        else:
            tvg_logo = home

        links = collect_links(ev.get("channel", {}))
        if links:
            for link in links:
                out.append(f'#EXTINF:-1 tvg-logo="{tvg_logo}" group-title="{group}",{title}')
                out.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
                out.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
                out.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
                out.append(link)

    # Live slider (tanpa thumbnail khusus)
    for ch in sliders:
        title = ch.get("title", "Live Channel")
        live = ch.get("liveTV", {})
        links = collect_links(live)
        for link in links:
            out.append(f'#EXTINF:-1 tvg-logo="{DEFAULT_LOGO}" group-title="PixelSport - Live",{title}')
            out.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            out.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            out.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            out.append(link)

    return "\n".join(out)


# ==============================================
# MAIN EXECUTION
# ==============================================

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

        print("[✓] Playlist Saved:", OUTPUT_FILE)
        print(f"[✓] Total Events: {len(events)}")
        print(f"[✓] Total Sliders: {len(sliders)}")

    except Exception as e:
        print("[X] ERROR:", e)


if __name__ == "__main__":
    main()
