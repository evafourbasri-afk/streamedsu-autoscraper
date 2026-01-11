import json, asyncio, re
import requests
from playwright.async_api import async_playwright

JSON_URL = "https://api.ppv.to/api/streams"
OUT_FILE = "ppv_exoplayer.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://ppv.to/"
}

async def extract_hls(iframe):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(iframe, timeout=60000)

        hls = None

        async def intercept(req):
            nonlocal hls
            url = req.url
            if ".m3u8" in url and "poocloud" in url:
                hls = url

        page.on("request", intercept)

        await page.wait_for_timeout(8000)
        await browser.close()
        return hls


async def main():
    data = requests.get(JSON_URL, headers=HEADERS).json()
    m3u = "#EXTM3U\n\n"

    for cat in data["streams"]:
        group = cat["category"]

        for ch in cat["streams"]:
            name = ch["name"]
            logo = ch["poster"]
            iframe = ch["iframe"]

            print("Extract:", name)

            hls = await extract_hls(iframe)
            if not hls:
                print(" ❌ no HLS")
                continue

            print(" ✔", hls)

            m3u += f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n'
            m3u += f'#EXTVLCOPT:http-referrer=https://modistreams.org/\n'
            m3u += f'#EXTVLCOPT:http-origin=https://modistreams.org\n'
            m3u += f'#EXTVLCOPT:http-user-agent=Mozilla/5.0\n'
            m3u += hls + "\n\n"

    open(OUT_FILE, "w").write(m3u)
    print("Saved:", OUT_FILE)

asyncio.run(main())
