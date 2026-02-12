import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

API_URL = "https://stream.skor5.com/api/live_streaming/getLiveList?type=3"
OUTPUT_M3U = "skor5_live.m3u"

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://stream.skor5.com/",
    "Origin": "https://stream.skor5.com",
}


def fetch_live_matches():
    r = requests.get(API_URL, headers=COMMON_HEADERS, timeout=20)
    r.raise_for_status()
    js = r.json()

    matches = []
    for item in js.get("data", {}).get("data", []):
        if item.get("islive") == 1 and item.get("id"):
            matches.append({
                "id": item["id"],
                "title": item.get("title", "LIVE MATCH"),
                "thumb": item.get("thumb", ""),
            })
    return matches


async def grab_m3u8_for_match(context, match):
    page = await context.new_page()
    embed_url = f"https://stream.skor5.com/embed/stream/?id={match['id']}"

    m3u8_url = None

    async def intercept(route, request):
        nonlocal m3u8_url
        url = request.url
        if ".m3u8" in url and "live8818.com" in url and not m3u8_url:
            m3u8_url = url
        await route.continue_()

    await context.route("**/*", intercept)

    try:
        await page.goto(embed_url, timeout=60000)
        await page.wait_for_timeout(20000)
    except Exception:
        pass

    await page.close()
    return m3u8_url


async def main():
    matches = fetch_live_matches()
    print(f"📡 LIVE MATCH FOUND: {len(matches)}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )

        m3u_entries = []

        for match in matches:
            print(f"🌐 OPENING: {match['title']}")
            m3u8 = await grab_m3u8_for_match(context, match)

            if not m3u8:
                print("❌ M3U8 NOT FOUND")
                continue

            print(f"🔥 M3U8 OK: {m3u8}")

            entry = f"""#EXTINF:-1 tvg-id="{match['id']}" tvg-logo="{match['thumb']}" group-title="Skor5 LIVE",{match['title']}
#EXTVLCOPT:http-referrer=https://stream.skor5.com/
#EXTVLCOPT:http-origin=https://stream.skor5.com
#EXTVLCOPT:http-user-agent=Mozilla/5.0
{m3u8}
"""
            m3u_entries.append(entry)

            await asyncio.sleep(3)

        await browser.close()

    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# Generated: {datetime.utcnow().isoformat()} UTC\n")
        for e in m3u_entries:
            f.write(e)

    print(f"\n✅ M3U GENERATED: {OUTPUT_M3U}")
    print(f"📺 TOTAL CHANNELS: {len(m3u_entries)}")


if __name__ == "__main__":
    asyncio.run(main())
