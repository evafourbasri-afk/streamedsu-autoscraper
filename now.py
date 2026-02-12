import requests

JSON_URL = "https://tvnow.my.id/c518s63iycqh9vn/movies.json"
OUTPUT_FILE = "movnow.m3u"

def main():
    r = requests.get(JSON_URL, timeout=30)
    r.raise_for_status()
    data = r.json()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for item in data:
            name = item.get("name", "Unknown")
            info = item.get("info", {})
            video = item.get("video", "")
            headers = item.get("headers", {})

            poster = info.get("poster", "")
            year = info.get("year", "")
            rating = info.get("rating", "")
            genres = ", ".join(g.capitalize() for g in info.get("genre", [])) or "Movies"

            ua = headers.get("user-agent", "")
            ref = headers.get("referer", "")

            title = f"{name} ({year})" if year else name
            star = f" ⭐{rating}" if rating else ""

            f.write(
                f'#EXTINF:-1 tvg-name="{title}" '
                f'tvg-logo="{poster}" '
                f'group-title="{genres}",{title}{star}\n'
            )

            if ua:
                f.write(f"#EXTVLCOPT:http-user-agent={ua}\n")
            if ref:
                f.write(f"#EXTVLCOPT:http-referrer={ref}\n")

            f.write(video + "\n\n")

    print("✅ movnow.m3u updated")

if __name__ == "__main__":
    main()