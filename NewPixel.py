import os
import json
import urllib.request
from urllib.error import URLError, HTTPError
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO

import requests
from PIL import Image, ImageDraw

# ================================
# CONFIG DASAR
# ================================
BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
OUTPUT_M3U = "NewPixel.m3u8"
THUMB_DIR = "thumbs"

# Header yang TERBUKTI jalan di pixel.py lama
VLC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
VLC_REFERER = f"{BASE}/"
VLC_ICY = "1"

# Peta logo event (sudah kamu upload di GitHub)
EVENT_LOGO_MAP = {
    "NFL": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NFL.png",
    "NHL": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NHL.png",
    "NBA": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/NBA.png",
    "MLB": "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/event_logos/MLB.png",
}

# Ukuran canvas sama seperti PPV
THUMB_W, THUMB_H = 512, 288
LOGO_SIZE = 130   # home / away
EVENT_SIZE = 85   # logo liga di tengah


# ================================
# FUNGSI FETCH JSON (VERSI LAMA, AMAN)
# ================================
def fetch_json(url):
    headers = {
        "User-Agent": VLC_USER_AGENT,
        "Referer": VLC_REFERER,
        "Accept": "*/*",
        "Connection": "close",
        "Icy-MetaData": VLC_ICY,
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


# ================================
# GRADIENT BACKGROUND (SAMA SEPERTI SEBELUMNYA)
# ================================
def build_gradient():
    img = Image.new("RGB", (THUMB_W, THUMB_H), "#000000")
    draw = ImageDraw.Draw(img)

    # tiga warna: biru gelap -> ungu -> merah gelap
    colors = [
        (20, 30, 80),    # dark blue
        (60, 20, 90),    # deep purple
        (120, 30, 60),   # dark red/pink
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


# ================================
# DOWNLOAD & RESIZE LOGO
# ================================
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


# ================================
# BANGUN THUMB 512x288
# ================================
def build_thumb(home_url, away_url, event_logo_url, filename):
    bg = build_gradient()

    home = fetch_logo(home_url, LOGO_SIZE)
    away = fetch_logo(away_url, LOGO_SIZE)
    evl  = fetch_logo(event_logo_url, EVENT_SIZE)

    # posisi tengah vertical
    center_y = THUMB_H // 2

    # home di kiri
    if home:
        x = 100
        y = center_y - home.height // 2
        bg.paste(home, (x, y), home)

    # away di kanan
    if away:
        x = THUMB_W - 100 - away.width
        y = center_y - away.height // 2
        bg.paste(away, (x, y), away)

    # event logo di tengah
    if evl:
        x = THUMB_W // 2 - evl.width // 2
        y = center_y - evl.height // 2
        bg.paste(evl, (x, y), evl)

    filepath = os.path.join(THUMB_DIR, filename)
    bg.save(filepath, "PNG")
    return filepath


# ================================
# UTILITY: KONVERSI WAKTU KE WIB
# ================================
def format_wib(timestamp_ms):
    """
    PixelSport biasanya kirim ms (epoch milliseconds).
    Kalau ternyata detik, tinggal dibagi logika ini nanti.
    """
    try:
        ts = int(timestamp_ms)
    except (TypeError, ValueError):
        return ""

    # asumsikan ms
    if ts > 10_000_000_000:  # sederhana: > tahun 2286 kalau detik
        ts /= 1000

    dt_utc = datetime.fromtimestamp(ts, tz=ZoneInfo("UTC"))
    dt_wib = dt_utc.astimezone(ZoneInfo("Asia/Jakarta"))
    return dt_wib.strftime("%d %b %Y %H:%M WIB")


# ================================
# SCRAPER UTAMA
# ================================
def scrape_pixel():
    os.makedirs(THUMB_DIR, exist_ok=True)

    print("[*] Fetching PixelSport events...")
    try:
        data = fetch_json(API_EVENTS)
    except Exception as e:
        print("[X] Gagal ambil JSON dari PixelSport:", e)
        return

    events = data.get("events", []) if isinstance(data, dict) else []

    lines = ["#EXTM3U"]

    for ev in events:
        title = ev.get("match_name", "Unknown Event").strip()

        # nama tim / logo
        home_logo = ev.get("competitors1_logo")
        away_logo = ev.get("competitors2_logo")

        # kategori liga: NFL, NBA, MLB, NHL
        raw_cat = ev.get("channel", {}).get("TVCategory", {}).get("name", "")
        league = (raw_cat or "").upper()
        if league not in ("NFL", "NBA", "MLB", "NHL"):
            # selain 4 liga itu skip saja
            continue

        # logo event di tengah
        event_logo_url = EVENT_LOGO_MAP.get(league)

        # waktu WIB (kalau ada)
        wib_str = format_wib(ev.get("start_time"))
        if wib_str:
            title = f"{title} | {wib_str}"

        # nama file thumb
        event_id = ev.get("id") or ev.get("_id") or "0"
        thumb_name = f"{league}_{event_id}.png"
        thumb_path = build_thumb(home_logo, away_logo, event_logo_url, thumb_name)

        # URL thumb di GitHub raw
        thumb_url = (
            "https://raw.githubusercontent.com/evafourbasri-afk/"
            "streamedsu-autoscraper/main/" + thumb_path.replace("\\", "/")
        )

        # ambil link stream
        chan = ev.get("channel", {}) or {}
        links = []
        for i in range(1, 4):
            u = chan.get(f"server{i}URL")
            if u and str(u).lower() != "null":
                links.append(u)

        if not links:
            continue

        group_title = f"PixelSport - {league}"

        for link in links:
            lines.append(
                f'#EXTINF:-1 tvg-logo="{thumb_url}" group-title="{group_title}",{title}'
            )
            lines.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            lines.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            lines.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            lines.append(link)

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[✓] Saved: {OUTPUT_M3U} ({len(events)} events total)")


if __name__ == "__main__":
    scrape_pixel()
