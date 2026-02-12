import json
import urllib.request
from datetime import datetime

JSON_URL = "https://raw.githubusercontent.com/drnewske/areallybadideabuttidonthateitijusthateitsomuch/refs/heads/main/matches.json"
OUTPUT_FILE = "matches.m3u"

FALLBACK_LOGO = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Tennis_icon.svg/512px-Tennis_icon.svg.png"

def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (OgieTV-M3U-Generator)"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def main():
    data = fetch_json(JSON_URL)

    lines = ["#EXTM3U"]

    for item in data:
        match_id = item.get("id", "")
        title = item.get("title", "Unknown Match")
        sport = item.get("sport", "sports").upper()
        is_live = item.get("isLive", False)

        group = f"{sport} - {'LIVE' if is_live else 'UPCOMING'}"

        logo = (
            item.get("team1", {}).get("logo")
            or item.get("team2", {}).get("logo")
            or FALLBACK_LOGO
        )

        links = item.get("links", [])
        if not links:
            continue

        # pilih link terbaik (HD + English)
        best = sorted(
            links,
            key=lambda x: (x.get("hd", False), x.get("language", "") == "English"),
            reverse=True
        )[0]

        url = best.get("url")
        if not url:
            continue

        kickoff = item.get("kickOff", "")
        if kickoff:
            try:
                kickoff = datetime.fromisoformat(kickoff).strftime("%Y-%m-%d %H:%M")
            except:
                pass

        name = title
        if kickoff:
            name += f" ({kickoff})"

        lines.append(
            f'#EXTINF:-1 tvg-id="{match_id}" tvg-name="{title}" group-title="{group}" tvg-logo="{logo}",{name}'
        )
        lines.append(url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"OK: wrote {OUTPUT_FILE} with {(len(lines)-1)//2} items")

if __name__ == "__main__":
    main()
