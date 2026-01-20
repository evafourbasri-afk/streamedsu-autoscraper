import requests
import json
from datetime import datetime

# ==========================
# INPUT
# ==========================
JSON_FILE = "feed.json"   # simpan JSON Anda di file ini
OUTPUT_M3U = "volleyball.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://zapp-5434-volleyball-tv.web.app/"
}

# ==========================
# LOAD JSON
# ==========================
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

entries = data.get("entry", [])

# ==========================
# INIT M3U
# ==========================
m3u = [
    "#EXTM3U"
]

# ==========================
# PROCESS ENTRIES
# ==========================
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
        r = requests.get(jw_api, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            print(f"[SKIP] {title} → JW API {r.status_code}")
            continue

        jw = r.json()
        sources = jw.get("playlist", [{}])[0].get("sources", [])

        hls_url = None
        for s in sources:
            if s.get("type") in ["application/vnd.apple.mpegurl", "hls"]:
                hls_url = s.get("file")
                break

        if not hls_url:
            print(f"[NO HLS] {title}")
            continue

        m3u.append(
            f'#EXTINF:-1 tvg-logo="{poster}" group-title="Volleyball",{title}'
        )
        m3u.append(hls_url)

        print(f"[OK] {title}")

    except Exception as ex:
        print(f"[ERROR] {title} → {ex}")

# ==========================
# SAVE M3U
# ==========================
with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
    f.write("\n".join(m3u))

print(f"\nDONE → {OUTPUT_M3U}")
