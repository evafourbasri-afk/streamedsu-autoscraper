import requests
import json
import re
from bs4 import BeautifulSoup

JSON_URL = "https://api.ppv.to/api/streams"   # endpoint JSON PPV.to
OUT_FILE = "ppv_exoplayer.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://ppv.to/",
    "Origin": "https://ppv.to"
}

IFRAME_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://modistreams.org/",
    "Origin": "https://modistreams.org"
}


def extract_m3u8(iframe_url):
    try:
        r = requests.get(iframe_url, headers=IFRAME_HEADERS, timeout=15)
        html = r.text

        found = re.findall(r'https?:\/\/[^"\']+\.m3u8[^"\']*', html)
        if found:
            return found[0]

        soup = BeautifulSoup(html, "html.parser")
        for s in soup.find_all("script"):
            if s.string:
                m = re.search(r'(https.*?\.m3u8[^"\']*)', s.string)
                if m:
                    return m.group(1)
    except:
        pass

    return None


def main():
    print("Downloading PPV JSON…")
    data = requests.get(JSON_URL, headers=HEADERS, timeout=20).json()

    m3u = "#EXTM3U\n\n"

    for cat in data["streams"]:
        group = cat["category"]

        for ch in cat["streams"]:
            name = ch["name"]
            logo = ch["poster"]
            iframe = ch["iframe"]

            print("Extract:", name)
            m3u8 = extract_m3u8(iframe)

            if not m3u8:
                print("  ❌ no stream")
                continue

            m3u += f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n'
            m3u += f'#EXTVLCOPT:http-referrer=https://modistreams.org/\n'
            m3u += f'#EXTVLCOPT:http-origin=https://modistreams.org\n'
            m3u += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)\n'
            m3u += m3u8 + "\n\n"

    open(OUT_FILE, "w", encoding="utf-8").write(m3u)
    print("Saved", OUT_FILE)


if __name__ == "__main__":
    main()
