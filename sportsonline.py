import asyncio
from playwright.async_api import async_playwright

URLS = [
    ("Newcastle United vs Manchester City", "https://sportsonline.cv/channels/hd/hd1.php"),
    ("NBA Boston Celtics vs Indiana Pacers", "https://sportsonline.cv/channels/pt/sporttv1.php"),
    ("NBA Boston Celtics vs Indiana Pacers (BR)", "https://sportsonline.cv/channels/bra/br6.php"),
]

OUT = "sportsonline.m3u"

async def grab(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        hls = None

        async def on_req(req):
            nonlocal hls
            if ".m3u8" in req.url:
                hls = req.url

        page.on("request", on_req)

        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(8000)
        await browser.close()
        return hls

async def main():
    with open(OUT, "w") as f:
        f.write("#EXTM3U\n")

        for name, url in URLS:
            print("Checking:", name)
            hls = await grab(url)

            if hls:
                print("FOUND:", hls)
                f.write(f'#EXTINF:-1 group-title="Sportsonline",{name}\n')
                f.write(hls + "\n")
            else:
                print("NO STREAM:", name)

    print("Saved:", OUT)

asyncio.run(main())
