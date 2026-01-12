import requests
import re
import os

# URL sumber playlist M3U Anda
SOURCE_M3U_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/matches.m3u"

# Header agar tidak diblokir oleh server streaming
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://embedsports.top/'
}

def get_direct_m3u8(embed_url):
    """Fungsi untuk mengambil link .m3u8 dari dalam halaman embed"""
    try:
        # Menghindari error jika baris kosong
        if not embed_url.startswith('http'):
            return embed_url
            
        print(f"Grabbing: {embed_url}")
        response = requests.get(embed_url, headers=HEADERS, timeout=15)
        
        # Mencari link .m3u8 menggunakan Regex
        # Mencari pola link yang ada di dalam script player
        found_links = re.findall(r'["\'](https?://[^\s\'"]+\.m3u8[^\s\'"]*)["\']', response.text)
        
        if found_links:
            # Membersihkan karakter backslash jika ada
            direct_link = found_links[0].replace("\\", "")
            print(f"Success -> Found .m3u8")
            return direct_link
        else:
            print(f"Failed -> No .m3u8 found in source")
            return embed_url
            
    except Exception as e:
        print(f"Error grabbing {embed_url}: {e}")
        return embed_url

def main():
    print(f"Mengambil playlist dari: {SOURCE_M3U_URL}")
    try:
        response = requests.get(SOURCE_M3U_URL)
        response.raise_for_status()
        lines = response.text.splitlines()
    except Exception as e:
        print(f"Gagal mengambil file sumber: {e}")
        return

    new_playlist = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('http'):
            # Jika baris adalah URL, lakukan grabbing
            direct_link = get_direct_m3u8(line)
            new_playlist.append(direct_link)
        else:
            # Jika baris adalah tag #EXTINF dsb, biarkan saja
            new_playlist.append(line)

    # Simpan hasil ke file playlist.m3u
    with open('playlist.m3u', 'w', encoding='utf-8') as f:
        f.write("\n".join(new_playlist))
    
    print("\nPROSES SELESAI!")
    print(f"File 'playlist.m3u' telah berhasil dibuat dengan {len(new_playlist)} baris.")

if __name__ == "__main__":
    main()
