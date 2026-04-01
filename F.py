import requests
import re
import os

def generate_m3u():
    url = "https://parlay12.serv00.net/fifaa.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    matches = content.split("======================================================================")
    
    m3u_content = "#EXTM3U\n"

    for block in matches:
        if not block.strip():
            continue

        # Ekstrak Judul
        title_match = re.search(r"Match: (.*)", block)
        title = title_match.group(1).strip() if title_match else "Unknown Match"

        # Ekstrak DRM License
        drm_match = re.search(r"DRM  : (.*)", block)
        license_url = drm_match.group(1).strip() if drm_match else ""

        # Ekstrak URL MPD khusus versi HD saja
        mpd_hd_match = re.search(r"\[\+\] MPD \(HD\) \[N\/A\]: (.*)", block)
        
        if mpd_hd_match:
            stream_url = mpd_hd_match.group(1).strip()
            
            m3u_content += f'\n#EXTINF:-1 group-title="FIFA Series", {title}\n'
            m3u_content += f'#KODIPROP:inputstream.adaptive.license_type=widevine\n'
            m3u_content += f'#KODIPROP:inputstream.adaptive.license_key={license_url}\n'
            m3u_content += f'{stream_url}\n'

    # Simpan ke file f.m3u
    with open("f.m3u", "w") as f:
        f.write(m3u_content)
    print("File f.m3u berhasil diperbarui!")

if __name__ == "__main__":
    generate_m3u()
