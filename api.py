import re
import base64
import requests
import sys

def get_param(name, default=None):
    for arg in sys.argv:
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
    return default

id_value = get_param("id", "mlb/2025-09-16/8204-lad")
source = get_param("source", "ppv.to")

urls = []

if source == "playembed.top":
    urls.append(f"https://playembed.top/embed/{id_value}")
    urls.append(f"https://ppv.to/embed/{id_value}")
else:
    urls.append(f"https://ppv.to/embed/{id_value}")
    urls.append(f"https://playembed.top/embed/{id_value}")

def extract_playlist_url(html):
    m = re.search(r"file:\s*'([^']+)'", html)
    if m:
        return m.group(1)

    m = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html)
    if m:
        return m.group(1)

    m = re.search(r'atob\s*\(\s*[\'"]([A-Za-z0-9\/=]+)[\'"]\s*\)', html)
    if m:
        try:
            return base64.b64decode(m.group(1)).decode("utf-8")
        except:
            pass

    m = re.search(r'const\s+\w+\s*=\s*atob\s*\(\s*[\'"]([A-Za-z0-9/\-_+=]+)[\'"]\s*\)', html)
    if m:
        try:
            return base64.b64decode(m.group(1)).decode("utf-8")
        except:
            pass

    return None

headers = {
    "accept": "text/html",
    "referer": f"https://ppv.to/live/{id_value}",
    "user-agent": "Mozilla/5.0",
}

playlist = None

for url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=10)
    except:
        continue

    if r.status_code == 200:
        playlist = extract_playlist_url(r.text)
        if playlist:
            break

if playlist:
    print(playlist)
else:
    print("URL File Playlist tidak ditemukan.")
