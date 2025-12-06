import requests
import json
from datetime import datetime

API_URL = "https://embedsports.top/data/events.json"
ORIGIN = "https://embedsports.top"
REFERRER = "https://embedsports.top/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

def get_events():
    r = requests.get(API_URL, timeout=15)
    return r.json()

def build_line(event):
    sport = event.get("sport", "Sports")
    name = event.get("name", "Unknown Event")
    logo = event.get("badge", "")
    m3u8 = event.get("playlist", "")

    tvg_id = f"{sport}.Dummy.us"
    group = f"StreamedSU - {sport}"

    return f'''#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}
#EXTVLCOPT:http-origin={ORIGIN}
#EXTVLCOPT:http-referrer={REFERRER}
#EXTVLCOPT:user-agent={UA}
{m3u8}
'''

def build_m3u():
    data = get_events()
    out = "#EXTM3U\n"
    for e in data:
        out += build_line(e)
    return out

if __name__ == "__main__":
    m3u = build_m3u()
    with open("StreamedSU.m3u8", "w", encoding="utf-8") as f:
        f.write(m3u)
