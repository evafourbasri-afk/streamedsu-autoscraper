import requests
import re

WORKER = "https://str.rizaleva01.workers.dev/?url="

BASE_MATCHES = "https://streamed.pk/api/matches/{cat}"
BASE_STREAM  = "https://streamed.pk/api/stream/{source}/{id}"

CATEGORIES = {
    "football": "Football",
    "basketball": "NBA",
    "american-football": "NFL",
    "fight": "UFC",
    "hockey": "NHL",
    "baseball": "MLB",
    "tennis": "Tennis",
    "cricket": "Cricket",
    "rugby": "Rugby",
    "motor-sports": "Racing",
    "darts": "Darts"
}

def clean(t):
    return re.sub(r"[^\x00-\x7F]+", "", t or "")

def normalize(data):
    if isinstance(data, dict):
        return data.get("streams", [])
    if isinstance(data, list):
        return data
    return []

out = ["#EXTM3U"]

print("StreamedSU IPTV Generator (Worker Enabled)")
print("========================================")

total = 0

for api_cat, name in CATEGORIES.items():
    print(f"\nFetching {name}...")
    try:
        matches = requests.get(BASE_MATCHES.format(cat=api_cat), timeout=15).json()
    except:
        print("  Failed")
        continue

    for m in matches:
        title = clean(m.get("name"))
        logo  = m.get("logo") or ""
        for s in m.get("sources", []):
            api = BASE_STREAM.format(source=s["source"], id=s["id"])
            try:
                data = requests.get(api, timeout=10).json()
            except:
                continue

            for st in normalize(data):
                url = st.get("url")
                if not url or ".m3u8" not in url:
                    continue

                proxied = WORKER + url

                out.append(
                    f'#EXTINF:-1 tvg-name="{title}" tvg-logo="{logo}" group-title="StreamedSU - {name}",{title}'
                )
                out.append(proxied)

                total += 1
                print("  OK:", title)
                break

with open("stream.m3u8", "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("\nDONE")
print("Streams:", total)
print("Output : stream.m3u8")
