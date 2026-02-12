import requests

# ==========================
# CONFIG
# ==========================
FEED_URL = "https://zapp-5434-volleyball-tv.web.app/jw/playlists/eMqXVhhW"
OUTPUT_M3U = "volleyball.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://zapp-5434-volleyball-tv.web.app/"
}

print("Fetching feed...")

r = requests.get(FEED_URL, headers=HEADERS, timeout=15)
r.raise_for_status()

data = r.json()
entries = data.get("entry", [])

m3u = ["#EXTM3U"]

for e in entries:
    media_id = e.get("id")
    title = e.get("title", "Unknown Match")

    poster = ""
    media_group = e.get("media_group", [])
    if media_group:
        items = media_group[0].get("media_item", [])
        if items:
            poster = items[-1].get("src", "")

    jw_api = f"https://cdn.jwplayer.com/v2/media/{media_id}"

    try:
        jr = requests.get(jw_api, headers=HEADERS, timeout=10)
        if jr.status_code != 200:
            print(f"[SKIP] {title} → JW API {jr.status_code}")
            continue

        jw = jr.json()
        playlist = jw.get("playlist", [])
        if not playlist:
            print(f"[NO PLAYLIST] {title}")
            continue

        sources = playlist[0].get("sources", [])
        hls = None

        for s in sources:
            if s.get("type") in ["application/vnd.apple.mpegurl", "hls"]:
                hls = s.get("file")
                break

        if not hls:
            print(f"[NO HLS] {title}")
            continue

        m3u.append(
            f'#EXTINF:-1 tvg-logo="{poster}" group-title="Volleyball",{title}'
        )
        m3u.append(hls)

        print(f"[OK] {title}")

    except Exception as ex:
        print(f"[ERROR] {title} → {ex}")

with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
    f.write("\n".join(m3u))

print(f"\nDONE → {OUTPUT_M3U}")
