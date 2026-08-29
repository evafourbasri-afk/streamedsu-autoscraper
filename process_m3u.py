import os
import re
import requests
from PIL import Image, ImageDraw
from rembg import remove
from io import BytesIO

# ================================
# KONFIGURASI
# ================================
M3U_FILE = "playlist.m3u"
LOGO_DIR = "logos"
# Sesuaikan dengan URL raw repositori Anda
REPO_URL = "https://raw.githubusercontent.com/srhady/bingstream/main/logos"

THUMB_W, THUMB_H = 512, 288
LOGO_SIZE = 180

os.makedirs(LOGO_DIR, exist_ok=True)

# ================================
# MEMBUAT BACKGROUND GRADASI
# ================================
def build_gradient():
    img = Image.new("RGB", (THUMB_W, THUMB_H), "#000000")
    draw = ImageDraw.Draw(img)

    # Warna: Biru Gelap -> Ungu -> Merah Gelap
    colors = [
        (20, 30, 80),    
        (60, 20, 90),    
        (120, 30, 60),   
    ]

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
# PROSES GAMBAR UTAMA
# ================================
def process_logo(url, filename):
    try:
        # 1. Unduh gambar
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        input_img = Image.open(BytesIO(r.content)).convert("RGBA")

        # 2. Hapus background bawaan
        logo_transparan = remove(input_img)

        # 3. Resize logo agar proporsional
        logo_transparan.thumbnail((LOGO_SIZE, LOGO_SIZE), Image.Resampling.LANCZOS)

        # 4. Buat background gradasi dan tempel logo di tengah
        bg = build_gradient()
        x = (THUMB_W - logo_transparan.width) // 2
        y = (THUMB_H - logo_transparan.height) // 2
        
        bg.paste(logo_transparan, (x, y), logo_transparan)

        # 5. Simpan hasil
        output_path = os.path.join(LOGO_DIR, filename)
        bg.save(output_path, "PNG")
        
        return f"{REPO_URL}/{filename}"
    except Exception as e:
        print(f"[!] Gagal memproses {url}: {e}")
        return url # Kembalikan URL asli jika gagal

# ================================
# EKSEKUSI FILE M3U
# ================================
def main():
    if not os.path.exists(M3U_FILE):
        print(f"File {M3U_FILE} tidak ditemukan.")
        return

    with open(M3U_FILE, 'r', encoding='utf-8') as f:
        m3u_content = f.read()

    pattern = r'tvg-logo="(https?://[^"]+)"'
    
    def replace_logo(match):
        original_url = match.group(1)
        
        # Lewati jika logo sudah berasal dari folder repositori kita
        if REPO_URL in original_url:
            return match.group(0)
            
        # Buat nama file berdasarkan hash URL agar unik dan aman
        filename = f"logo_{abs(hash(original_url))}.png"
            
        print(f"Memproses: {original_url} ...")
        new_url = process_logo(original_url, filename)
        return f'tvg-logo="{new_url}"'

    # Ganti semua URL tvg-logo di dalam teks
    new_m3u_content = re.sub(pattern, replace_logo, m3u_content)

    # Simpan kembali ke file M3U
    with open(M3U_FILE, 'w', encoding='utf-8') as f:
        f.write(new_m3u_content)
    
    print("[✓] Selesai. playlist.m3u telah diperbarui dengan logo baru.")

if __name__ == "__main__":
    main()
