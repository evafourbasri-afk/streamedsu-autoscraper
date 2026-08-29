import os
import re
import requests
from PIL import Image
from rembg import remove
from io import BytesIO

# Konfigurasi Path
M3U_FILE = 'playlist.m3u'
OUTPUT_DIR = 'images'
# Sesuaikan dengan format raw URL GitHub Anda
REPO_URL = 'https://raw.githubusercontent.com/srhady/bingstream/main/images'

os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_gradient_bg(width, height, color_left, color_right):
    """Membuat background gradasi horizontal."""
    base = Image.new('RGB', (width, height), color_left)
    top = Image.new('RGB', (width, height), color_right)
    mask = Image.new('L', (width, height))
    mask_data = [int(255 * (x / width)) for y in range(height) for x in range(width)]
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def process_image(url, filename):
    # 1. Unduh gambar asli
    response = requests.get(url)
    input_img = Image.open(BytesIO(response.content)).convert("RGBA")

    # 2. Hapus background bawaan (menjadikan logo transparan)
    logo_transparan = remove(input_img)

    # 3. Buat background gradasi (Resolusi 1280x720, warna Teal ke Merah Gelap)
    bg = create_gradient_bg(1280, 720, (0, 77, 64), (128, 0, 0)) 

    # 4. Resize logo transparan agar proporsional
    logo_transparan.thumbnail((500, 500), Image.Resampling.LANCZOS)
    
    # 5. Pusatkan logo di atas background
    x = (bg.width - logo_transparan.width) // 2
    y = (bg.height - logo_transparan.height) // 2
    
    # Tempelkan logo menggunakan channel alpha-nya sendiri sebagai mask
    bg.paste(logo_transparan, (x, y), logo_transparan)
    
    # Simpan hasil akhir
    output_path = os.path.join(OUTPUT_DIR, filename)
    bg.save(output_path, "JPEG", quality=90)
    
    return f"{REPO_URL}/{filename}"

def main():
    with open(M3U_FILE, 'r', encoding='utf-8') as f:
        m3u_content = f.read()

    # Regex untuk mencari URL pada parameter tvg-logo
    pattern = r'tvg-logo="(https?://[^"]+)"'
    
    def replace_logo(match):
        original_url = match.group(1)
        
        # Lewati jika logo sudah berasal dari folder repo lokal kita
        if REPO_URL in original_url:
            return match.group(0)
            
        # Buat nama file aman berdasarkan nama file asli
        filename = original_url.split('/')[-1].split('?')[0]
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            filename = f"logo_{abs(hash(original_url))}.jpg"
        else:
            # Paksa ekstensi output menjadi .jpg
            filename = filename.rsplit('.', 1)[0] + '.jpg'
            
        print(f"Memproses: {original_url} ...")
        try:
            new_url = process_image(original_url, filename)
            return f'tvg-logo="{new_url}"'
        except Exception as e:
            print(f"Gagal memproses {original_url}: {e}")
            return match.group(0)

    # Timpa konten M3U dengan URL yang baru
    new_m3u_content = re.sub(pattern, replace_logo, m3u_content)

    with open(M3U_FILE, 'w', encoding='utf-8') as f:
        f.write(new_m3u_content)
    
    print("Selesai. playlist.m3u telah diperbarui.")

if __name__ == "__main__":
    main()
