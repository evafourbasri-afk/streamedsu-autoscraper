import requests
import re

HEADERS = {
    "Referer": "https://embedsports.top/",
    "Origin": "https://embedsports.top",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

BASE_MATCHES = "https://streamed.pk/api/matches/{cat}"
BASE_STREAM  = "https://streamed.pk/api/stream/{source}/{id}"

CATEGORIES = {
    "football": "Football",
    "basketball": "NBA",
    "american-football": "NFL",
    "fight": "UFC / Boxing",
    "hockey": "NHL",
    "baseball": "MLB",
    "tennis": "Tennis",
    "cricket": "Cricket",
    "rugby": "Rugby",
    "motor-sports": "Racing",
    "darts": "Darts"
}

def clean(text):
    return re.sub(r"[^\x00-\x7F]+", "", text or "")

def normalize_streams(data):
    # API kadang: { streams:[...] }
    # kadang: [...]
    if isinstance(data, dict):
        return data.get("streams", [])
    if isinstance(data, list):
        return data
    return []

out = ["#EXTM3U"]

print("StreamedSU IPTV Generator")
print("=========================")

total = 0

for cat_api, cat_name in CATEGORIES.items():
    print(f"\nFetching {cat_name}...")
    try:
        matches = requests.get(BASE_MATCHES.format(cat=cat_api), timeout=15).json()
    except Exception as e:
        print("  Failed:", e)
        continue

    for match in matches:
        title = clean(match.get("name"))
        logo  = match.get("logo") or ""
        sources = match.get("sources", [])

        for src in sources:
            api = BASE_STREAM.format(source=src["source"], id=src["id"])
            try:
                data = requests.get(api, timeout=10).json()
            except:
                continue

            streams = normalize_streams(data)

            for s in streams:
                url = s.get("url")
                if not url or ".m3u8" not in url:
                    continue

                out.append(
                    f'#EXTINF:-1 tvg-name="{title}" tvg-logo="{logo}" group-title="StreamedSU - {cat_name}",{title}'
                )
                out.append("#EXTVLCOPT:http-origin=https://embedsports.top")
                out.append("#EXTVLCOPT:http-referrer=https://embedsports.top/")
                out.append("#EXTVLCOPT:user-agent=Mozilla/5.0")
                out.append(url)

                total += 1
                print("  OK:", title)
                break

with open("stream.m3u8", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("\nDONE")
print("Streams:", total)
print("Output : stream.m3u8")
