import json
import urllib.request
import requests
from urllib.error import URLError, HTTPError

BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"
OUTPUT_FILE = "NewPixel.m3u8"

LOGO_SOURCE_M3U = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/ppvsortir.m3u"

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

def get_league_group(raw_name):
    if not raw_name:
        return "PixelSport - Other"
    name = raw_name.lower()
    for key, cat in LEAGUE_MAP.items():
        if key in name:
            return f"PixelSport - {cat}"
    return "PixelSport - Other"

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

def load_logo_dict_from_m3u(url):
    try:
        print("[*] Loading external M3U logos...")
        r = requests.get(url, timeout=10)
        lines = r.text.splitlines()
    except Exception as e:
        print("[X] Failed loading M3U:", e)
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
                logo_url = line.split('tvg-logo="')[1].split('"')[0]
                if logo_url:
                    logo_map[key] = logo_url
            except:
                pass

    print(f"[+] Loaded {len(logo_map)} logos.")
    return logo_map

def get_best_logo(team, logo_map):
    if not team:
        return None

    key = team.upper().replace(" ", "").replace(".", "")
    key4 = key[:4]

    if key4 in logo_map:
        return logo_map[key4]

    if key in logo_map:
        return logo_map[key]

    for k, url in logo_map.items():
        if key4 in k or k in key:
            return url

    return None

def collect_links(obj):
    links = []
    for i in range(1, 4):
        url = obj.get(f"server{i}URL")
        if url and url.lower() != "null":
            links.append(url)
    return links

def build_m3u(events, sliders, logo_map):
    out = ["#EXTM3U"]

    for ev in events:
        title = ev.get("match_name", "Unknown Event").strip()

        team1 = ev.get("competitors1_name") or title
        team2 = ev.get("competitors2_name")

        logo1 = get_best_logo(team1, logo_map)
        logo2 = get_best_logo(team2, logo_map)
        logo = logo1 or logo2 or ev.get("competitors1_logo", DEFAULT_LOGO)

        raw_cat = ev.get("channel", {}).get("TVCategory", {}).get("name", "")
        group_title = get_league_group(raw_cat)

        links = collect_links(ev.get("channel", {}))
        if not links:
            continue

        for link in links:
            out.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_title}",{title}')
            out.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            out.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            out.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            out.append(link)

    for ch in sliders:
        title = ch.get("title", "Live Channel")
        live = ch.get("liveTV", {})
        links = collect_links(live)
        if not links:
            continue

        for link in links:
            out.append(f'#EXTINF:-1 tvg-logo="{DEFAULT_LOGO}" group-title="PixelSport - Live",{title}')
            out.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            out.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            out.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            out.append(link)

    return "\n".join(out)

def main():
    try:
        logo_map = load_logo_dict_from_m3u(LOGO_SOURCE_M3U)

        print("[*] Fetching events...")
        events = fetch_json(API_EVENTS).get("events", [])

        print("[*] Fetching sliders...")
        sliders = fetch_json(API_SLIDERS).get("data", [])

        m3u = build_m3u(events, sliders, logo_map)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(m3u)

        print(f"[✓] Saved as {OUTPUT_FILE}")
        print(f"[✓] Events: {len(events)}, Sliders: {len(sliders)}")

    except Exception as e:
        print("[X] ERROR:", e)

if __name__ == "__main__":
    main()
