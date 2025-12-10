import json
import urllib.request
import requests
from urllib.error import URLError, HTTPError

BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"

# ===============================
#   OUTPUT M3U NAME CHANGED HERE
# ===============================
OUTPUT_FILE = "NewPixel.m3u8"

LOGO_SOURCE_M3U = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/ppvsortir.m3u"

VLC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
VLC_REFERER = f"{BASE}/"
VLC_ICY = "1"

DEFAULT_LOGO = "https://pixelsport.tv/static/media/PixelSportLogo.1182b5f687c239810f6d.png"


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
        return json.loads(resp.read().decode("utf-8"))


def load_logo_dict_from_m3u(m3u_url):
    try:
        print("[*] Loading logo source M3U...")
        r = requests.get(m3u_url, timeout=10)
        lines = r.text.splitlines()
    except Exception as e:
        print("[X] Logo M3U load failed:", e)
        return {}

    logo_map = {}

    for line in lines:
        if not line.startswith("#EXTINF"):
            continue

        try:
            name = line.split(",")[-1].strip()
            key = name.upper().replace(" ", "").replace(".", "")
        except:
            continue

        if 'tvg-logo="' in line:
            try:
                logo = line.split('tvg-logo="')[1].split('"')[0]
                if logo:
                    logo_map[key] = logo
            except:
                pass

    print(f"[+] {len(logo_map)} logos loaded from external M3U.")
    return logo_map


def get_best_logo(team_name, logo_map):
    if not team_name:
        return None

    name_key = team_name.upper().replace(" ", "").replace(".", "")
    key4 = name_key[:4]

    if key4 in logo_map:
        return logo_map[key4]

    if name_key in logo_map:
        return logo_map[name_key]

    for k, url in logo_map.items():
        if key4 in k or k in name_key:
            return url

    return None


def collect_links(obj):
    links = []
    for i in range(1, 4):
        key = f"server{i}URL"
        url = obj.get(key)
        if url and url.lower() != "null":
            links.append(url)
    return links


def build_m3u(events, sliders, logo_map):
    lines = ["#EXTM3U"]

    for ev in events:
        title = ev.get("match_name", "Unknown Event").strip()

        team1 = ev.get("competitors1_name") or title
        team2 = ev.get("competitors2_name")

        logo1 = get_best_logo(team1, logo_map)
        logo2 = get_best_logo(team2, logo_map)

        logo = logo1 or logo2 or ev.get("competitors1_logo", DEFAULT_LOGO)

        links = collect_links(ev.get("channel", {}))
        if not links:
            continue

        for link in links:
            lines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="Pixelsports",{title}')
            lines.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            lines.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            lines.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            lines.append(link)

    for ch in sliders:
        title = ch.get("title", "Live Channel")
        live = ch.get("liveTV", {})
        links = collect_links(live)
        if not links:
            continue

        for link in links:
            lines.append(f'#EXTINF:-1 tvg-logo="{DEFAULT_LOGO}" group-title="Pixelsports - Live",{title}')
            lines.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            lines.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            lines.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            lines.append(link)

    return "\n".join(lines)


def main():
    try:
        logo_map = load_logo_dict_from_m3u(LOGO_SOURCE_M3U)

        print("[*] Fetching PixelSport events...")
        events = fetch_json(API_EVENTS).get("events", [])

        print("[*] Fetching sliders...")
        sliders = fetch_json(API_SLIDERS).get("data", [])

        playlist = build_m3u(events, sliders, logo_map)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(playlist)

        print(f"[✓] Saved as {OUTPUT_FILE}")
        print(f"[✓] Events: {len(events)}, Sliders: {len(sliders)}")

    except Exception as e:
        print("[X] ERROR:", e)


if __name__ == "__main__":
    main()
