import requests
from datetime import datetime, timedelta
import pytz

# =====================================================
# CONFIG
# =====================================================
JSON_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/matches.json"
OUTPUT_M3U = "livemobox.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android; IPTV)"
}

UPCOMING_URL = "about:blank"
MATCH_DURATION = timedelta(hours=2)  # asumsi durasi match

WIB = pytz.timezone("Asia/Jakarta")

# =====================================================
# HELPER
# =====================================================
def is_m3u8(url: str) -> bool:
    return isinstance(url, str) and ".m3u8" in url.lower()

def fetch_json(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def parse_wib_datetime(date_str, time_str):
    """
    date: DD-MM-YYYY
    time: HH:MM
    """
    dt = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
    return WIB.localize(dt)

# =====================================================
# MAIN
# =====================================================
def main():
    data = fetch_json(JSON_URL)
    now_wib = datetime.now(WIB)

    m3u = ["#EXTM3U"]
    cnt_live = cnt_upcoming = cnt_end = 0

    for item in data:
        links = item.get("links", [])
        m3u8_links = [u for u in links if is_m3u8(u)]

        title = item.get("match_title_from_api", "Unknown Match")
        competition = item.get("competition", "SPORT")
        match_id = item.get("match_id", "")
        logo = item.get("team1", {}).get("logo_url", "")
        date_wib = item.get("date", "")
        time_wib = item.get("time", "")

        kickoff = parse_wib_datetime(date_wib, time_wib)
        end_time = kickoff + MATCH_DURATION

        # =========================
        # STATUS DETECTION
        # =========================
        if now_wib > end_time:
            status = "[END]"
            urls = [UPCOMING_URL]
            cnt_end += 1

        elif now_wib >= kickoff and m3u8_links:
            status = "[LIVE]"
            urls = m3u8_links
            cnt_live += 1

        else:
            status = "[UPCOMING]"
            urls = [UPCOMING_URL]
            cnt_upcoming += 1

        channel_name = f"{status} {title} | {date_wib} {time_wib} WIB"

        for url in urls:
            m3u.append(
                f'#EXTINF:-1 tvg-id="{match_id}" '
                f'tvg-logo="{logo}" '
                f'group-title="{competition}",'
                f'{channel_name}'
            )
            m3u.append(url)

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))

    print(f"✅ Generated {OUTPUT_M3U}")
    print(f"🔴 LIVE     : {cnt_live}")
    print(f"🕒 UPCOMING : {cnt_upcoming}")
    print(f"⚫ END      : {cnt_end}")

# =====================================================
if __name__ == "__main__":
    main()
