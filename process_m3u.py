import os
import re
import requests
import concurrent.futures
from PIL import Image, ImageDraw
from rembg import remove
from io import BytesIO

# ================================
# KONFIGURASI
# ================================
SOURCE_URL = "https://raw.githubusercontent.com/srhady/bingstream/main/playlist.m3u"
OUTPUT_M3U = "PlaylistRizal.m3u"
LOGO_DIR = "logos"
REPO_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/logos"

THUMB_W, THUMB_H = 512, 288
LOGO_MAX_WIDTH = 400
LOGO_MAX_HEIGHT = 200
MAX_WORKERS = 2 # Memproses 4 gambar sekaligus

os.makedirs(LOGO_DIR, exist_ok=True)

# ================================
# MEMBUAT BACKGROUND GRADASI
# ================================
def build_gradient():
    img = Image.new("RGB", (THUMB_W, THUMB_H), "#000000")
    draw = ImageDraw.Draw(img)
    colors = [(20, 30, 80), (60, 20, 90), (120, 30, 60)]

    for x in range(THUMB_W):
        t = x / THUMB_W
        if t < 0.5:
            t2 = t * 2
            r = int(colors[0][0] * (1 - t2) + colors[1][0] * t2)
            g = int(colors[0][1] * (1 - t2) + colors[1][1] * t2)
            b = int(colors[0][2] * (1 - t2) + colors[1][2] * t2)
        else:
            t2 = (t - 0.5) * 2
            r = int(colors[1][0] * (1 - t2) + colors[2][0] * t2)
            g = int(colors[1][1] * (1 - t2) + colors[2][1] * t2)
            b = int(colors[1][2] * (1 - t2) + colors[2][2] * t2)
        draw.line([(x, 0), (x, THUMB_H)], fill=(r, g, b))
    return img

# ================================
# PROSES GAMBAR INDIVIDUAL
# ================================
def process_logo(url):
    # Hindari memproses ulang URL dari repo sendiri
    if REPO_URL in url:
        return url, url

    filename = f"logo_{abs(hash(url))}.png"
    output_path = os.path.join(LOGO_DIR, filename)
    final_url = f"{REPO_URL}/{filename}"

    # CACHE LOKAL: Jika gambar sudah pernah dibuat sebelumnya, langsung gunakan
    if os.path.exists(output_path):
        return url, final_url

    print(f"[*] Mengunduh & Memproses: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        input_img = Image.open(BytesIO(r.content)).convert("RGBA")

        logo_transparan = remove(input_img)
        logo_transparan.thumbnail((LOGO_MAX_WIDTH, LOGO_MAX_HEIGHT), Image.Resampling.LANCZOS)

        bg = build_gradient()
        
        x = (THUMB_W - logo_transparan.width) // 2
        y = (THUMB_H - logo_transparan.height) // 2
        bg.paste(logo_transparan, (x, y), logo_transparan)

        bg.save(output_path, "PNG")
        return url, final_url
    except Exception as e:
        print(f"[!] Gagal: {url} -> {e}")
        return url, url 

# ================================
# EKSEKUSI PENGAMBILAN & KONVERSI
# ================================
def main():
    print(f"[*] Mengunduh playlist dari sumber: {SOURCE_URL}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = requests.get(SOURCE_URL, headers=headers)
        req.raise_for_status()
        m3u_content = req.text
    except Exception as e:
        print(f"[X] Gagal mengunduh playlist sumber: {e}")
        return

    # Kumpulkan semua URL unik dari file M3U
    pattern = r'tvg-logo="(https?://[^"]+)"'
    all_urls = set(re.findall(pattern, m3u_content))
    
    print(f"[*] Ditemukan {len(all_urls)} logo unik. Memulai multithreading...")
    
    # Jalankan pemrosesan secara paralel (Multithreading)
    processed_urls = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(process_logo, all_urls)
        for original, new in results:
            processed_urls[original] = new

    # Fungsi untuk menimpa teks
    def replace_logo(match):
        return f'tvg-logo="{processed_urls.get(match.group(1), match.group(1))}"'

    print("[*] Merakit file M3U baru...")
    new_m3u_content = re.sub(pattern, replace_logo, m3u_content)

    with open(OUTPUT_M3U, 'w', encoding='utf-8') as f:
        f.write(new_m3u_content)
    
    print(f"[✓] Selesai! Playlist baru disimpan dengan nama: {OUTPUT_M3U}")

if __name__ == "__main__":
    main()
