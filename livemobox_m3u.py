import os
import requests
from datetime import datetime, timedelta, timezone

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
# MAIN
# =====================================================
def main():
    data = fetch_json(JSON_URL)
    now_wib = datetime.now(WIB)

    m3u = ["#EXTM3U"]

    for item in data:
        title = item.get("match_title_from_api", "Unknown Match")
        competition = item.get("competition", "SPORT")
        match_id = item.get("match_id", "0")
        date_wib = item.get("date", "")
        time_wib = item.get("time", "")

        # 🔥 PAKAI LOGO PNG ASLI (TRANSPARAN)
        home_logo = item.get("team1", {}).get("logo_url")
        away_logo = item.get("team2", {}).get("logo_url")

        # Pilih salah satu (lebih bersih di grid)
        tvg_logo = home_logo or away_logo or ""

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

        channel_name = f"{status} {title} | {date_wib} {time_wib} WIB"

        for url in urls:
            m3u.append(
                f'#EXTINF:-1 tvg-id="{match_id}" '
                f'tvg-logo="{tvg_logo}" '
                f'group-title="{competition}",{channel_name}'
            )
            m3u.append(url)

    os.makedirs("dist", exist_ok=True)
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print("✅ FINAL: livemobox.m3u (TRANSPARENT LOGO MODE)")

# =====================================================
if __name__ == "__main__":
    main()
