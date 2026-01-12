import requests
import re
import base64
import os

SOURCE_M3U_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/matches.m3u"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://embedsports.top/',
    'Accept-Language': 'en-US,en;q=0.9'
}

def decode_base64_links(text):
    """Mencoba mencari dan mendekode string Base64 yang mungkin berisi URL"""
    potential_base64 = re.findall(r'[A-Za-z0-9+/]{30,}=', text)
    for b in potential_base64:
        try:
            decoded = base64.b64decode(b).decode('utf-8')
            if '.m3u8' in decoded or '.mpd' in decoded:
                return decoded
        except:
            continue
    return None

def get_direct_stream(embed_url):
    try:
        if not embed_url.startswith('http'): return embed_url
        print(f"Scanning: {embed_url}")
        
        response = requests.get(embed_url, headers=HEADERS, timeout=15)
        html = response.text

        # 1. Cari langsung .m3u8 atau .mpd (DASH)
        links = re.findall(r'["\'](https?://[^\s\'"]+\.(?:m3u8|mpd)[^\s\'"]*)["\']', html)
        if links:
            return links[0].replace("\\", "")

        # 2. Coba decode Base64 jika tidak ditemukan link mentah
        b64_link = decode_base64_links(html)
        if b64_link:
            print(f"  -> Found via Base64 Decode")
            return b64_link

        # 3. Cari pola 'source: "URL"' atau 'file: "URL"' yang umum di player JS
        js_links = re.findall(r'(?:file|source|src)\s*[:=]\s*["\'](https?://[^"\']+)["\']', html)
        for j in js_links:
            if '.m3u8' in j or '.mpd' in j or 'stream' in j:
                return j.replace("\\", "")

        print(f"  -> Failed: Link tetap tidak terlihat di HTML statis")
        return embed_url
            
    except Exception as e:
        print(f"  -> Error: {e}")
        return embed_url

def main():
    print(f"Fetching source playlist...")
    try:
        r = requests.get(SOURCE_M3U_URL)
        lines = r.text.splitlines()
    except: return

    new_playlist = []
    for line in lines:
        if line.startswith('http'):
            new_playlist.append(get_direct_stream(line.strip()))
        else:
            new_playlist.append(line)

    with open('playlist.m3u', 'w', encoding='utf-8') as f:
        f.write("\n".join(new_playlist))
    print("\nUpdate Selesai.")

if __name__ == "__main__":
    main()
