import requests
import re
import os

# Konfigurasi Header agar tidak diblokir
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://embedsports.top/'
}

def get_direct_m3u8(embed_url):
    try:
        print(f"Mencoba grab: {embed_url}")
        response = requests.get(embed_url, headers=HEADERS, timeout=15)
        # Mencari pola link m3u8 di dalam source code
        links = re.findall(r'["\'](https?://[^\s\'"]+\.m3u8[^\s\'"]*)["\']', response.text)
        if links:
            # Mengambil link pertama yang ditemukan
            return links[0].replace("\\", "")
    except Exception as e:
        print(f"Error pada {embed_url}: {e}")
    return embed_url # Kembalikan link asli jika gagal

def process_m3u():
    if not os.path.exists('input.m3u'):
        print("File input.m3u tidak ditemukan!")
        return

    with open('input.m3u', 'r') as f:
        lines = f.readlines()

    new_playlist = []
    for line in lines:
        line = line.strip()
        if line.startswith('http'):
            # Ini adalah baris URL, kita grab link m3u8-nya
            direct_link = get_direct_m3u8(line)
            new_playlist.append(direct_link)
        else:
            # Ini adalah baris tag (#EXTM3U atau #EXTINF)
            new_playlist.append(line)

    with open('playlist.m3u', 'w') as f:
        f.write("\n".join(new_playlist))
    print("Update selesai! File playlist.m3u telah diperbarui.")

if __name__ == "__main__":
    process_m3u()
