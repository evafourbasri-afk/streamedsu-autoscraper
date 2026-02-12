import asyncio
from playwright.async_api import async_playwright
import requests
import re

SOURCE_M3U_URL = "https://raw.githubusercontent.com/evafourbasri-afk/streamedsu-autoscraper/refs/heads/main/matches.m3u"

async def get_m3u8_dynamic(browser, embed_url):
    """Membuka browser dan menangkap link .m3u8 dari network traffic"""
    page = await browser.new_page()
    m3u8_link = embed_url # Default balik ke link asli jika gagal
    
    try:
        # Listener untuk menangkap semua request jaringan
        def handle_request(request):
            nonlocal m3u8_link
            if ".m3u8" in request.url:
                m3u8_link = request.url

        page.on("request", handle_request)

        print(f"Browsing: {embed_url}")
        # Buka halaman dengan timeout 30 detik
        await page.goto(embed_url, wait_until="networkidle", timeout=60000)
        # Beri waktu tambahan 5 detik agar player inisialisasi
        await asyncio.sleep(5) 
        
    except Exception as e:
        print(f"  -> Error/Timeout: {e}")
    finally:
        await page.close()
    
    return m3u8_link

async def main():
    print("Mengambil playlist sumber...")
    r = requests.get(SOURCE_M3U_URL)
    lines = r.text.splitlines()

    async with async_playwright() as p:
        # Jalankan browser Chromium
        browser = await p.chromium.launch(headless=True)
        new_playlist = []

        for line in lines:
            line = line.strip()
            if line.startswith("http"):
                direct_link = await get_m3u8_dynamic(browser, line)
                new_playlist.append(direct_link)
                if direct_link != line:
                    print(f"  -> SUCCESS: Found M3U8")
            else:
                new_playlist.append(line)

        await browser.close()

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(new_playlist))
    print("\nUpdate Selesai!")

if __name__ == "__main__":
    asyncio.run(main())
