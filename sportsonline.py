import asyncio
from playwright.async_api import async_playwright

URL = "https://sportsonline.cv/channels/hd/hd1.php"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        hls = None

        async def handle_request(req):
            nonlocal hls
            if ".m3u8" in req.url:
                hls = req.url
                print("FOUND HLS:", hls)

        page.on("request", handle_request)

        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(10000)

        if not hls:
            print("NO HLS FOUND")
        else:
            print("\nFINAL STREAM:\n", hls)

        await browser.close()

asyncio.run(run())
