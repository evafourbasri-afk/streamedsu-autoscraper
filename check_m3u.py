import re
import concurrent.futures
import requests

INPUT_FILE = "playlist_ch01-ch400.m3u"
OUTPUT_LIVE = "live_channels.m3u"
TIMEOUT = 5  # Waktu tunggu maksimal (detik)

def parse_m3u(file_path):
    channels = []
    current_title = ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"File {file_path} tidak ditemukan.")
        return channels

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            current_title = line
        elif line and not line.startswith("#"):
            if current_title:
                channels.append({"title": current_title, "url": line})
                current_title = ""
    return channels

def check_channel(channel):
    try:
        # Menggunakan GET dengan stream=True agar tidak mendownload seluruh video stream
        response = requests.get(channel["url"], timeout=TIMEOUT, stream=True, headers={"User-Agent": "VLC"})
        # Status code 200-299 atau beberapa server merespons 403/302 tapi stream tetap aktif
        if response.status_code < 400:
            return channel, True
    except Exception:
        pass
    return channel, False

def main():
    print(f"Membaca file {INPUT_FILE}...")
    channels = parse_m3u(INPUT_FILE)
    print(f"Total channel ditemukan: {len(channels)}. Memulai pengecekan...")

    live_channels = []
    
    # Menggunakan ThreadPoolExecutor untuk mempercepat proses pengecekan paralel
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_channel, ch): ch for ch in channels}
        for future in concurrent.futures.as_completed(futures):
            ch, is_live = future.result()
            if is_live:
                print(f"[LIVE] {ch['url']}")
                live_channels.append(ch)
            else:
                print(f"[DEAD] {ch['url']}")

    # Simpan channel yang hidup ke file M3U baru
    with open(OUTPUT_LIVE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in live_channels:
            f.write(f"{ch['title']}\n{ch['url']}\n")

    print(f"\nSelesai! {len(live_channels)} channel aktif disimpan ke {OUTPUT_LIVE}")

if __name__ == "__main__":
    main()
