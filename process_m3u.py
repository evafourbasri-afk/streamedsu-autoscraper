import os
import re
import requests
from PIL import Image, ImageDraw
from rembg import remove
from io import BytesIO

# ================================
# KONFIGURASI
# ================================
# URL sumber playlist asli
SOURCE_URL = "https://raw.githubusercontent.com/srhady/bingstream/main/playlist.m3u"

# Nama file playlist hasil konversi
OUTPUT_M3U = "PlaylistRizal.m3u"
LOGO_DIR = "logos"

# URL Raw ke repositori Anda
REPO_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/main/logos"

# Ukuran Canvas (Background)
THUMB_W, THUMB_H = 512, 288

# Ukuran Maksimal Logo (DIPERBESAR agar logo klub yang berdampingan tidak kekecilan)
LOGO_MAX_WIDTH = 440
LOGO_MAX_HEIGHT = 240

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
# PROSES GAMBAR
# ================================
def process_logo(url, filename):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        
        # 1. Unduh gambar asli
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        input_img = Image.open(BytesIO(r.content)).convert("RGBA")

        # 2. Hapus background bawaannya
        logo_transparan = remove(input_img)
        
        # 3. Perbesar ukuran logo agar memenuhi ruang dengan proporsional
        logo_transparan.thumbnail((LOGO_MAX_WIDTH, LOGO_MAX_HEIGHT), Image.Resampling.LANCZOS)

        # 4. Buat background gradasi
        bg = build_gradient()
        
        # 5. Letakkan logo persis di tengah
        x = (THUMB_W - logo_transparan.width) // 2
        y = (THUMB_H - logo_transparan.height) // 2
        bg.paste(logo_transparan, (x, y), logo_transparan)

        # Simpan
        output_path = os.path.join(LOGO_DIR, filename)
        bg.save(output_path, "PNG")
        
        return f"{REPO_URL}/{filename}"
    except Exception as e:
        print(f"[!] Gagal memproses {url}: {e}")
        return url 

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

    pattern = r'tvg-logo="(https?://[^"]+)"'
    processed_urls = {}
    
    def replace_logo(match):
        original_url = match.group(1)
        
        # Hindari memproses ulang URL dari repo sendiri
        if REPO_URL in original_url:
            return match.group(0)
            
        # Gunakan Cache
        if original_url in processed_urls:
            return f'tvg-logo="{processed_urls[original_url]}"'
            
        filename = f"logo_{abs(hash(original_url))}.png"
            
        print(f"Memproses: {original_url} ...")
        new_url = process_logo(original_url, filename)
        
        processed_urls[original_url] = new_url
        return f'tvg-logo="{new_url}"'

    print("[*] Memulai konversi logo...")
    new_m3u_content = re.sub(pattern, replace_logo, m3u_content)

    with open(OUTPUT_M3U, 'w', encoding='utf-8') as f:
        f.write(new_m3u_content)
    
    print(f"[✓] Selesai! Playlist baru disimpan dengan nama: {OUTPUT_M3U}")

if __name__ == "__main__":
    main()
