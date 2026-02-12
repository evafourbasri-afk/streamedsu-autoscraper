import requests
import json
from datetime import datetime

OUTPUT_FILE = "playlist.m3u8"

url = "https://api.ppv.to/api/streams"

headers = {
    "accept": "*/*",
    "referer": "https://ppv.to/",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64)"
}

response = requests.get(url, headers=headers)
data = response.json()

if not data or "streams" not in data:
    with open(OUTPUT_FILE, "w") as f:
        f.write("#EXTM3U\n# ERROR mengambil data\n")
    exit()

# 🔥 API Python kamu di GitHub
API_LINK = "https://raw.githubusercontent.com/evafourbasri-afk/ppv-m3u/main/api.py"

m3u_output = "#EXTM3U\n\n"

for category in data["streams"]:
    for item in category["streams"]:

        name = item.get("name", "Unknown")
        tag = item.get("tag", "Unknown")
        poster = item.get("poster", "")
        uri_name = item.get("uri_name", "")

        if "24/7" in tag:
            continue

        ts = item.get("starts_at", 0)
        time_wib = datetime.fromtimestamp(ts).strftime("%H:%M")
        date_wib = datetime.fromtimestamp(ts).strftime("%d/%m/%Y")

        m3u_output += (
            f'#EXTINF:-1 group-title="{tag}" tvg-logo="{poster}",'
            f'{time_wib} - {date_wib} | {name}\n'
        )
        m3u_output += "#EXTVLCOPT:http-referrer=https://ppv.to/\n"
        m3u_output += f"{API_LINK}?id={uri_name}\n\n"

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(m3u_output)

print("playlist.m3u8 berhasil dibuat!")
