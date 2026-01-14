import requests

# =====================================================
# CONFIG
# =====================================================
JSON_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/matches.json"
OUTPUT_M3U = "livemobox.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Android; IPTV)"
}

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def is_m3u8(url: str) -> bool:
    """Check if URL is m3u8 stream"""
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
    total_streams = 0

    for item in data:
        links = item.get("links", [])
        m3u8_links = [u for u in links if is_m3u8(u)]

        if not m3u8_links:
            continue

        title = item.get("match_title_from_api", "Unknown Match")
        time_wib = item.get("time", "")
        competition = item.get("competition", "LIVE")
        match_id = item.get("match_id", "")
        logo = item.get("team1", {}).get("logo_url", "")

        for stream_url in m3u8_links:
            extinf = (
                f'#EXTINF:-1 '
                f'tvg-id="{match_id}" '
                f'tvg-logo="{logo}" '
                f'group-title="{competition}",'
                f'{title} | {time_wib} WIB'
            )

            m3u_lines.append(extinf)
            m3u_lines.append(stream_url)
            total_streams += 1

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    print(f"✅ Generated {OUTPUT_M3U} with {total_streams} m3u8 streams")

# =====================================================
if __name__ == "__main__":
    main()
