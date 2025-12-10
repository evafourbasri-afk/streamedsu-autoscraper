import json
import urllib.request
from urllib.error import URLError, HTTPError

BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
API_SLIDERS = f"{BASE}/backend/slider/getSliders"
OUTPUT_FILE = "Pixelsports.m3u8"

LIVE_TV_LOGO = "https://pixelsport.tv/static/media/PixelSportLogo.1182b5f687c239810f6d.png"
LIVE_TV_ID = "24.7.Dummy.us"

VLC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
VLC_REFERER = f"{BASE}/"
VLC_ICY = "1"

LEAGUE_INFO = {
    "NFL": ("NFL.Dummy.us", "NFL"),
    "MLB": ("MLB.Baseball.Dummy.us", "MLB"),
    "NHL": ("NHL.Hockey.Dummy.us", "NHL"),
    "NBA": ("NBA.Basketball.Dummy.us", "NBA"),
    "NASCAR": ("Racing.Dummy.us", "NASCAR"),
    "UFC": ("UFC.Fight.Pass.Dummy.us", "UFC"),
    "SOCCER": ("Soccer.Dummy.us", "Soccer"),
    "BOXING": ("PPV.EVENTS.Dummy.us", "Boxing"),
}


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


def collect_links(obj):
    links = []
    if not obj:
        return links
    for i in range(1, 4):
        key = f"server{i}URL"
        url = obj.get(key)
        if url and url.lower() != "null":
            links.append(url)
    return links


def get_league_info(name):
    name_lower = name.lower()
    for key, (tvid, group) in LEAGUE_INFO.items():
        if key.lower() in name_lower:
            return tvid, group
    return ("Pixelsports.Dummy.us", "Pixelsports")


def build_m3u(events, sliders):
    lines = ["#EXTM3U"]

    # =============================
    # EVENT DARI PIXELSPORT
    # =============================
    for ev in events:
        title = ev.get("match_name", "Unknown Event").strip()

        # Logo event asli (WAJIB)
        logo = ev.get("competitors1_logo", LIVE_TV_LOGO)

        league = ev.get("channel", {}).get("TVCategory", {}).get("name", "Sports")
        tvid, group_display = get_league_info(league)

        links = collect_links(ev.get("channel", {}))
        if not links:
            continue

        for link in links:
            lines.append(
                f'#EXTINF:-1 tvg-id="{tvid}" tvg-logo="{logo}" group-title="Pixelsports - {group_display}",{title}'
            )
            lines.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            lines.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            lines.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            lines.append(link)

    # =============================
    # LIVE TV SLIDERS SECTION
    # =============================
    for ch in sliders:
        title = ch.get("title", "Live Channel").strip()
        live = ch.get("liveTV", {})
        links = collect_links(live)
        if not links:
            continue

        for link in links:
            lines.append(
                f'#EXTINF:-1 tvg-id="{LIVE_TV_ID}" tvg-logo="{LIVE_TV_LOGO}" group-title="Pixelsports - Live TV",{title}'
            )
            lines.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            lines.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            lines.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            lines.append(link)

    return "\n".join(lines)


def main():
    try:
        print("[*] Fetching PixelSport data...")
        events_data = fetch_json(API_EVENTS)
        events = events_data.get("events", [])

        sliders_data = fetch_json(API_SLIDERS)
        sliders = sliders_data.get("data", [])

        playlist = build_m3u(events, sliders)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(playlist)

        print(f"[+] Saved: {OUTPUT_FILE} ({len(events)} events + {len(sliders)} live channels)")
    except Exception as e:
        print(f"[!] Error: {e}")


if __name__ == "__main__":
    main()
