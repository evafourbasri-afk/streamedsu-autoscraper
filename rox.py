import logging
import re
from requests_html import HTMLSession

# =========================
# CONFIG
# =========================
BASE_URL = "https://roxiestreams.live"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz"

START_URLS = [
    BASE_URL,
    f"{BASE_URL}/nfl",
    f"{BASE_URL}/soccer",
    f"{BASE_URL}/mlb",
    f"{BASE_URL}/nba",
    f"{BASE_URL}/nhl",
    f"{BASE_URL}/fighting",
    f"{BASE_URL}/motorsports"
]

TV_INFO = {
    "soccer": ("Soccer.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/football.png?raw=true", "Soccer"),
    "nfl": ("Football.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nfl.png?raw=true", "Football"),
    "nba": ("NBA.Basketball.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nba.png?raw=true", "Basketball"),
    "mlb": ("MLB.Baseball.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/baseball.png?raw=true", "Baseball"),
    "nhl": ("NHL.Hockey.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nhl.png?raw=true", "Hockey"),
    "fighting": ("Combat.Sports.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/boxing.png?raw=true", "Combat Sports"),
    "ufc": ("UFC.Fight.Pass.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/mma.png?raw=true", "Combat Sports"),
    "motorsports": ("Racing.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/f1.png?raw=true", "Motorsports"),
}

DEFAULT_LOGO = "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/default.png?raw=true"

# FIXED REGEX (support .m3u8?token=xxx)
M3U8_REGEX = re.compile(
    r'https?://[^\s"\'<>`]+\.m3u8(?:\?[^\s"\'<>`]*)?'
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# =========================
# HELPERS
# =========================
def get_tv_info(url, title):
    combined = (url + title).lower()
    for key, (epg_id, logo, group) in TV_INFO.items():
        if key in combined:
            return epg_id, logo, group
    return "Sports.Rox.us", DEFAULT_LOGO, "General Sports"


# =========================
# MAIN
# =========================
def main():
    session = HTMLSession()
    playlist = [f'#EXTM3U x-tvg-url="{EPG_URL}"']

    seen_m3u8 = set()
    processed_events = set()

    for start_url in START_URLS:
        logging.info(f"Scanning for events at: {start_url}")
        try:
            r = session.get(start_url, timeout=20)

            # Event links
            event_links = r.html.find("#eventsTable a")

            for link in event_links:
                event_title = link.text.strip()
                event_url = list(link.absolute_links)[0]

                if event_url in processed_events:
                    continue
                processed_events.add(event_url)

                logging.info(f"Opening Event Page: {event_title}")

                try:
                    event_page = session.get(event_url, timeout=20)
                    event_page.html.render(sleep=4, timeout=30)

                    found_links = []

                    # 1️⃣ HTML
                    found_links.extend(M3U8_REGEX.findall(event_page.html.html))

                    # 2️⃣ SCRIPT JS (KEY FIX)
                    for s in event_page.html.find("script"):
                        if s.text:
                            found_links.extend(M3U8_REGEX.findall(s.text))

                    # 3️⃣ IFRAMES
                    for iframe in event_page.html.find("iframe"):
                        src = iframe.attrs.get("src", "")
                        if not src:
                            continue

                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = BASE_URL + src

                        try:
                            if "google" in src or "twitter" in src:
                                continue

                            iframe_page = session.get(src, timeout=15)
                            found_links.extend(M3U8_REGEX.findall(iframe_page.text))
                        except:
                            continue

                    # ADD STREAMS
                    for m3u8 in set(found_links):
                        if m3u8 in seen_m3u8:
                            continue

                        eid, logo, grp = get_tv_info(event_url, event_title)

                        playlist.append(
                            f'#EXTINF:-1 tvg-id="{eid}" tvg-logo="{logo}" group-title="{grp}",{event_title}'
                        )
                        playlist.append(m3u8)
                        seen_m3u8.add(m3u8)

                        logging.info(f"Added stream: {event_title}")

                except Exception as e:
                    logging.error(f"Event error: {e}")

        except Exception as e:
            logging.error(f"Failed to scan {start_url}: {e}")

    with open("Roxiestreams.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(playlist))

    logging.info(f"Scrape Complete. Total streams: {len(seen_m3u8)}")


if __name__ == "__main__":
    main()
