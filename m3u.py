import requests
import os
import re
import json
import sys
import time
import urllib.parse
import urllib3
from datetime import datetime, timedelta

try:
    from bs4 import BeautifulSoup
    from dateutil import parser
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: Missing required libraries. Please run: pip install requests beautifulsoup4 python-dateutil python-dotenv", file=sys.stderr)

# ==============================================================================
#           SETUP GLOBAL DAN DISABILITASI WARNINGS
# ==============================================================================

# Disabilita gli avvisi di sicurezza per le richieste senza verifica SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# MEMUAT VARIABEL LINGKUNGAN SEKALI DI AWAL
# Ini sangat penting agar GitHub Actions dapat membaca Secret FLARESOLVERR_URL
load_dotenv() 

# ==============================================================================
#           FUNGSI PEMBANTU UNTUK EKSTRAKSI STREAM M3U8
# ==============================================================================

def extract_m3u8_from_watch_page(watch_url, flaresolverr_url):
    """
    Menggunakan FlareSolverr untuk mengakses halaman watch.php dan 
    mengekstrak URL stream .m3u8 yang tersembunyi di dalam JavaScript.
    """
    print(f"-> Mencoba ekstraksi stream dari: {watch_url}")
    
    payload = {
        "cmd": "request.get",
        "url": watch_url,
        "maxTimeout": 120000 # Timeout lebih lama untuk stream
    }
    
    try:
        # Panggil FlareSolverr untuk mengakses halaman yang terproteksi
        response = requests.post(
            flaresolverr_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=70
        )
        response.raise_for_status()
        result = response.json()

        if result.get("status") != "ok":
            print(f"   ❌ FlareSolverr gagal untuk halaman watch: {result.get('message')}")
            return None

        html_content = result["solution"]["response"]
        
        # Cari tautan M3U8 yang disematkan dalam HTML/JS
        m3u8_match = re.search(r'(https?://[^"\']+\.(m3u8|ts|mpd)[^"\'\s]*)', html_content)
        
        if m3u8_match:
            stream_url = m3u8_match.group(1)
            # Membersihkan tautan dari karakter escape
            stream_url = stream_url.replace('\\u0026', '&').replace('&amp;', '&')
            print(f"   ✅ Stream M3U8 ditemukan: {stream_url}")
            return stream_url
        
        print("   ❌ Tautan stream M3U8 tidak ditemukan di halaman watch.")
        return None

    except Exception as e:
        print(f"   ❌ Error saat ekstraksi stream: {e}")
        return None

def search_m3u8_in_sites(channel_id, flaresolverr_url):
    """Fungsi pembantu yang mengarahkan ke halaman watch dan memulai ekstraksi."""
    watch_url = f"https://daddyhd.com/watch.php?id={channel_id}"
    return extract_m3u8_from_watch_page(watch_url, flaresolverr_url)


# ==============================================================================
#           FUNGSI UTAMA: DLHD (Daddylive)
# ==============================================================================

def dlhd():
    """
    Estrae canali 24/7 e eventi live da DaddyLive e li salva in un unico file M3U.
    Rimuove automaticamente i canali duplicati.
    """
    print("Eseguendo dlhd...")

    # Ambil variabel lingkungan yang sudah dimuat secara global
    FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL")
    if not FLARESOLVERR_URL:
        print("❌ ERRORE: Variabel 'FLARESOLVERR_URL' tidak diatur (diperlukan untuk dlhd).")
        return
    FLARESOLVERR_URL = FLARESOLVERR_URL.strip()

    JSON_FILE = "daddyliveSchedule.json"
    OUTPUT_FILE = "dlhd.m3u"

    # ========== FUNZIONI DI SUPPORTO ==========
    def clean_category_name(name):
        return re.sub(r'<[^>]+>', '', name).strip()

    # ========== ESTRAZIONE CANALI 24/7 ==========
    print("Estraendo canali 24/7 dalla pagina HTML...")
    html_url = "https://daddyhd.com/24-7-channels.php"

    try:
        print(f"Accesso a {html_url} con FlareSolverr...")
        payload = {
            "cmd": "request.get",
            "url": html_url,
            "maxTimeout": 120000
        }
        response = requests.post(
            FLARESOLVERR_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=70
        )
        response.raise_for_status()
        result = response.json()

        if result.get("status") != "ok":
            print(f"❌ FlareSolverr fallito per {html_url}: {result.get('message')}")
            raise Exception("FlareSolverr request failed")

        html_content = result["solution"]["response"]
        print("✓ Cloudflare bypassato con FlareSolverr!")
        
        # Parsa l'HTML con BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        cards = soup.find_all('a', class_='card')
        
        print(f"Trovati {len(cards)} channel links di halaman 24/7.")
 
        channels_247 = []
 
        for card in cards:
            title_div = card.find('div', class_='card__title')
            if not title_div: continue
            
            name = title_div.text.strip()
            href = card.get('href', '')
            if not ('id=' in href): continue
            
            channel_id = href.split('id=')[1].split('&')[0]
            
            if not name or not channel_id: continue

            # Correzioni nama
            if name == "Sky Calcio 7 (257) Italy":
                name = "DAZN"
            if channel_id == "853":
                name = "Canale 5 Italy"
            
            # Cerca lo stream .m3u8 menggunakan fungsi yang sudah diperbaiki
            stream_url = search_m3u8_in_sites(channel_id, FLARESOLVERR_URL)
            
            if stream_url:
                channels_247.append((name, stream_url))

        # Logika penamaan duplikat
        name_counts = {}
        for name, _ in channels_247:
            name_counts[name] = name_counts.get(name, 0) + 1
 
        final_channels = []
        name_counter = {}
 
        for name, stream_url in channels_247:
            if name_counts[name] > 1:
                if name not in name_counter:
                    name_counter[name] = 1
                    final_channels.append((name, stream_url))
                else:
                    name_counter[name] += 1
                    new_name = f"{name} ({name_counter[name]})"
                    final_channels.append((new_name, stream_url))
            else:
                final_channels.append((name, stream_url))

        print(f"Trovati {len(channels_247)} canali 24/7 dengan URL stream")
        channels_247 = final_channels
    except Exception as e:
        print(f"Errore nell'estrazione dei canali 24/7: {e}")
        channels_247 = []

    # ========== ESTRAZIONE EVENTI LIVE ==========
    print("Estraendo eventi live...")
    live_events = []

    if os.path.exists(JSON_FILE):
        try:
            now = datetime.now()
            yesterday_date = (now - timedelta(days=1)).date()

            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            categorized_channels = {}

            for date_key, sections in data.items():
                date_part = date_key.split(" - ")[0]
                try:
                    date_obj = parser.parse(date_part, fuzzy=True).date()
                except Exception as e:
                    print(f"Errore parsing data '{date_part}': {e}")
                    continue

                process_this_date = False
                is_yesterday_early_morning_event_check = False

                if date_obj == now.date():
                    process_this_date = True
                elif date_obj == yesterday_date:
                    process_this_date = True
                    is_yesterday_early_morning_event_check = True
                else:
                    continue

                if not process_this_date:
                    continue

                for category_raw, event_items in sections.items():
                    category = clean_category_name(category_raw)
                    if category.lower() == "tv shows":
                        continue
                    if category not in categorized_channels:
                        categorized_channels[category] = []

                    for item in event_items:
                        time_str = item.get("time", "00:00")
                        event_title = item.get("event", "Evento")

                        try:
                            original_event_time_obj = datetime.strptime(time_str, "%H:%M").time()
                            event_datetime_adjusted_for_display_and_filter = datetime.combine(date_obj, original_event_time_obj)

                            if is_yesterday_early_morning_event_check:
                                start_filter_time = datetime.strptime("00:00", "%H:%M").time()
                                end_filter_time = datetime.strptime("04:00", "%H:%M").time()
                                if not (start_filter_time <= original_event_time_obj <= end_filter_time):
                                    continue
                            else:
                                if now - event_datetime_adjusted_for_display_and_filter > timedelta(hours=2):
                                    continue

                            time_formatted = event_datetime_adjusted_for_display_and_filter.strftime("%H:%M")
                        except Exception as e_time:
                            print(f"Errore parsing orario '{time_str}' per evento '{event_title}' in data '{date_key}': {e_time}")
                            time_formatted = time_str

                        for ch in item.get("channels", []):
                            channel_name = ch.get("channel_name", "")
                            channel_id = ch.get("channel_id", "")

                            tvg_name = f"{event_title} ({time_formatted})"
                            categorized_channels[category].append({
                                "tvg_name": tvg_name,
                                "channel_name": channel_name,
                                "channel_id": channel_id,
                                "event_title": event_title,
                                "category": category
                            })

            # Converti in lista per il file M3U
            for category, channels in categorized_channels.items():
                for ch in channels:
                    try: 
                        # Cerca stream .m3u8 menggunakan fungsi yang sudah diperbaiki
                        stream = search_m3u8_in_sites(ch["channel_id"], FLARESOLVERR_URL)                        
                        if stream:
                            live_events.append((f"{category} | {ch['tvg_name']}", stream))
                    except Exception as e:
                        print(f"Errore su {ch['tvg_name']}: {e}")

            print(f"Trovati {len(live_events)} eventi live con URL stream")

        except Exception as e:
            print(f"Errore nell'estrazione degli eventi live: {e}")
            live_events = []
    else:
        print(f"File {JSON_FILE} tidak ditemukan, eventi live saltati")

    # ========== GENERAZIONE FILE M3U UNIFICATO ==========
    print("Generando file M3U unificato...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")

        # Aggiungi eventi live
        if live_events:
            f.write(f'#EXTINF:-1 group-title="Live Events DADDYLIVE",-- LIVE EVENTS --\n')
            f.write("https://example.com/playlist-separator.m3u8\n\n")

            for name, url in live_events:
                f.write(f'#EXTINF:-1 group-title="Live Events DADDYLIVE",{name}\n')
                f.write(f'{url}\n\n')

        # Aggiungi canali 24/7
        if channels_247:
            for name, url in channels_247:
                f.write(f'#EXTINF:-1 group-title="DLHD 24/7",{name}\n')
                f.write(f'{url}\n\n')

    total_channels = len(channels_247) + len(live_events)
    print(f"Creato file {OUTPUT_FILE} con {total_channels} canali totali.")


# ==============================================================================
#           FUNGSI: SCHEDULE EXTRACTOR
# ==============================================================================

def schedule_extractor():
    print("Eseguendo lo schedule_extractor.py...")

    # Ambil variabel lingkungan yang sudah dimuat secara global
    FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL")
    if not FLARESOLVERR_URL:
        print("❌ ERRORE: Variabel 'FLARESOLVERR_URL' tidak diatur (diperlukan untuk schedule_extractor).")
        return
    FLARESOLVERR_URL = FLARESOLVERR_URL.strip()

    LINK_DADDY = os.getenv("LINK_DADDY", "").strip() or "https://daddyhd.com"
    JSON_OUTPUT = "daddyliveSchedule.json"

    def html_to_json(html_content):
        """Converte il contenuto HTML della programmazione in formato JSON."""
        soup = BeautifulSoup(html_content, 'html.parser')
        result = {}
        
        schedule_div = soup.find('div', id='schedule') or soup.find('div', class_='schedule schedule--compact')
        
        if not schedule_div:
            print("AVVISO: Contenitore 'schedule' tidak ditemukan!")
            return {}
        
        day_title_tag = schedule_div.find('div', class_='schedule__dayTitle')
        current_date = day_title_tag.text.strip() if day_title_tag else "Unknown Date"
        
        result[current_date] = {}
        
        for category_div in schedule_div.find_all('div', class_='schedule__category'):
            cat_header = category_div.find('div', class_='schedule__catHeader')
            if not cat_header: continue
            
            cat_meta = cat_header.find('div', class_='card__meta')
            if not cat_meta: continue
            
            current_category = cat_meta.text.strip()
            result[current_date][current_category] = []
            
            category_body = category_div.find('div', class_='schedule__categoryBody')
            if not category_body: continue
            
            for event_div in category_body.find_all('div', class_='schedule__event'):
                event_header = event_div.find('div', class_='schedule__eventHeader')
                if not event_header: continue
                
                time_span = event_header.find('span', class_='schedule__time')
                event_title_span = event_header.find('span', class_='schedule__eventTitle')
                
                event_data = {
                    'time': time_span.text.strip() if time_span else '',
                    'event': event_title_span.text.strip() if event_title_span else 'Evento Sconosciuto',
                    'channels': []
                }
                
                channels_div = event_div.find('div', class_='schedule__channels')
                if channels_div:
                    for link in channels_div.find_all('a', href=True):
                        href = link.get('href', '')
                        channel_id_match = re.search(r'id=(\d+)', href)
                        if channel_id_match:
                            channel_id = channel_id_match.group(1)
                            channel_name = link.get('title', link.text.strip())
                            event_data['channels'].append({
                                'channel_name': channel_name,
                                'channel_id': channel_id
                            })
                
                if event_data['channels']:
                    result[current_date][current_category].append(event_data)
        return result
    
    def extract_schedule_container():
        url = f"{LINK_DADDY}/"
        
        print(f"Accesso a {url} con FlareSolverr...")
        payload = {"cmd": "request.get", "url": url, "maxTimeout": 60000}
        
        try:
            response = requests.post(FLARESOLVERR_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=70)
            result = response.json()
            
            if result.get("status") != "ok":
                print(f"❌ FlareSolverr fallito: {result.get('message')}")
                return False
            
            html_content = result["solution"]["response"]
            print("✓ Cloudflare bypassato con FlareSolverr!")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            schedule_div = soup.find('div', id='schedule') or soup.find('div', class_='schedule schedule--compact')
            
            if not schedule_div:
                print("❌ Container #schedule tidak ditemukan!")
                return False
            
            print("✓ Schedule diekstrak!")
            json_data = html_to_json(str(schedule_div))
            
            with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=4)
            
            print(f"✓ Salvato schedule in {JSON_OUTPUT}")
            return True
            
        except Exception as e:
            print(f"❌ ERRORE: {str(e)}")
            return False
    
    if not extract_schedule_container():
        print("Gagal mengekstrak schedule.")


# ==============================================================================
#           MAIN FUNCTION
# ==============================================================================

def main():
    print("Memulai eksekusi skrip DaddyLive...")
    try:
        # 1. Jalankan Schedule Extractor untuk membuat daddyliveSchedule.json
        try:
            schedule_extractor()
        except Exception as e:
            print(f"Errore durante l'esecuzione di schedule_extractor: {e}")
        
        # 2. Jalankan DLHD (yang bergantung pada file JSON dari schedule_extractor)
        try:
            dlhd()
        except Exception as e:
            print(f"Errore durante l'esecuzione di dlhd: {e}")
            
        print("Semua skrip yang diperlukan (schedule_extractor dan dlhd) telah selesai!")
    except Exception as e:
        print(f"Terjadi error fatal di main: {e}")

if __name__ == "__main__":
    main()
