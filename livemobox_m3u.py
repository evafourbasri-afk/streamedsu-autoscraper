import requests

# =====================================================
# CONFIG
# =====================================================
JSON_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/matches.json"
OUTPUT_M3U = "livemobox.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android; IPTV)"
}

UPCOMING_URL = "about:blank"  # aman untuk ExoPlayer / OTT

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def is_m3u8(url: str) -> bool:
    return isinstance(url, str) and ".m3u8" in url.lower()

def fetch_json(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

# =====================================================
# MAIN
# =====================================================
def main():
    data = fetch_json(JSON_URL)

    m3u_lines = ["#EXTM3U"]
    total_live = 0
    total_upcoming = 0

    for item in data:
        links = item.get("links", [])
        m3u8_links = [u for u in links if is_m3u8(u)]

        title = item.get("match_title_from_api", "Unknown Match")
        time_wib = item.get("time", "")
        date_wib = item.get("date", "")
        competition = item.get("competition", "LIVE")
        match_id = item.get("match_id", "")
        logo = item.get("team1", {}).get("logo_url", "")

        # ================================
        # LIVE
        # ================================
        if m3u8_links:
            channel_name = f"[LIVE] {title} | {date_wib} {time_wib} WIB"

            for stream_url in m3u8_links:
                extinf = (
                    f'#EXTINF:-1 '
                    f'tvg-id="{match_id}" '
                    f'tvg-logo="{logo}" '
                    f'group-title="{competition}",'
                    f'{channel_name}'
                )
                m3u_lines.append(extinf)
                m3u_lines.append(stream_url)
                total_live += 1

        # ================================
        # UPCOMING (TIDAK ADA LINK)
        # ================================
        else:
            channel_name = f"[UPCOMING] {title} | {date_wib} {time_wib} WIB"

            extinf = (
                f'#EXTINF:-1 '
                f'tvg-id="{match_id}" '
                f'tvg-logo="{logo}" '
                f'group-title="{competition}",'
                f'{channel_name}'
            )
            m3u_lines.append(extinf)
            m3u_lines.append(UPCOMING_URL)
            total_upcoming += 1

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    print(f"✅ Generated {OUTPUT_M3U}")
    print(f"   ▶ LIVE     : {total_live}")
    print(f"   ⏳ UPCOMING : {total_upcoming}")

# =====================================================
if __name__ == "__main__":
    main()
