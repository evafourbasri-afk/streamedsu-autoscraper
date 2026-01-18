import logging
from requests_html import HTMLSession
import re
import os

# Integrated Settings & Constants
BASE_URL = "https://roxiestreams.live"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz"

# Starting with the Home Page + Category Pages
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
    "motorsports": ("Racing.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/f1.png?raw=true", "Motorsports")
}

DEFAULT_LOGO = "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/default.png?raw=true"
M3U8_REGEX = re.compile(r'https?://[^\s"\'<>`]+\.m3u8')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_tv_info(url, title):
    combined = (url + title).lower()
    for key, (epg_id, logo, group) in TV_INFO.items():
        if key in combined:
            return epg_id, logo, group
    return "Sports.Rox.us", DEFAULT_LOGO, "General Sports"

def main():
    session = HTMLSession()
    playlist = [f'#EXTM3U x-tvg-url="{EPG_URL}"']
    seen_m3u8 = set()
    processed_events = set()

    for start_url in START_URLS:
        logging.info(f"Scanning for events at: {start_url}")
        try:
            r = session.get(start_url, timeout=15)
            # Find links specifically inside the events table
            event_links = r.html.find('#eventsTable a')
            
            for link in event_links:
                event_title = link.text.strip()
                event_url = list(link.absolute_links)[0]
                
                if event_url in processed_events:
                    continue
                
                logging.info(f"Opening Event Page: {event_title}")
                processed_events.add(event_url)
                
                try:
                    event_page = session.get(event_url, timeout=20)
                    # Render JS and wait 4 seconds for the player to initialize
                    event_page.html.render(sleep=4, timeout=30)
                    
                    # Search for m3u8 in the rendered HTML
                    found_links = M3U8_REGEX.findall(event_page.html.html)
                    
                    # If none found, look inside iframes
                    if not found_links:
                        for iframe in event_page.html.find('iframe'):
                            src = iframe.attrs.get('src', '')
                            if src:
                                if not src.startswith('http'):
                                    src = f"https:{src}" if src.startswith('//') else f"{BASE_URL}{src}"
                                try:
                                    if 'google' not in src and 'twitter' not in src:
                                        if_r = session.get(src, timeout=10)
                                        found_links.extend(M3U8_REGEX.findall(if_r.text))
                                except: continue

                    for m3u8 in found_links:
                        if m3u8 not in seen_m3u8:
                            # Verify the link is actually reachable
                            try:
                                head = session.get(m3u8, stream=True, timeout=5)
                                if head.status_code == 200:
                                    eid, logo, grp = get_tv_info(event_url, event_title)
                                    playlist.append(f'#EXTINF:-1 tvg-id="{eid}" tvg-logo="{logo}" group-title="{grp}",{event_title}')
                                    playlist.append(m3u8)
                                    seen_m3u8.add(m3u8)
                                    logging.info(f"Successfully added: {event_title}")
                            except: continue
                except Exception as e:
                    logging.error(f"Error processing {event_url}: {e}")
                    
        except Exception as e:
            logging.error(f"Could not access {start_url}: {e}")

    with open("Roxiestreams.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(playlist))
    logging.info(f"Scrape Complete. Total streams: {len(seen_m3u8)}")

if __name__ == "__main__":
    main()
