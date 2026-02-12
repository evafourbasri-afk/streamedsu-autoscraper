from flask import Flask, request, redirect, jsonify
import requests
import re
import base64

app = Flask(__name__)

# ============================
# EXTRACTOR
# ============================
def extract_playlist_url(html):

    # file: 'xxxx'
    m = re.search(r"file:\s*'([^']+)'", html)
    if m:
        return m.group(1)

    # source:".......m3u8"
    m = re.search(r'source:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html)
    if m:
        return m.group(1)

    # atob('BASE64')
    m = re.search(r"atob\(['\"]([A-Za-z0-9\/=]+)['\"]\)", html)
    if m:
        try:
            decoded = base64.b64decode(m.group(1)).decode()
            return decoded
        except:
            pass

    # const w = atob("XXXXX")
    m = re.search(r'atob\(["\']([A-Za-z0-9/\-_+=]+)["\']\)', html)
    if m:
        try:
            decoded = base64.b64decode(m.group(1)).decode()
            return decoded
        except:
            pass

    return None

# ============================
# MAIN API ENDPOINT
# ============================
@app.route("/api")
def api():

    stream_id = request.args.get("id")
    source = request.args.get("source", "ppv.to")

    if not stream_id:
        return jsonify({"error": "Missing id"}), 400

    urls = []

    # Priority switching
    if source == "playembed.top":
        urls.append(f"https://playembed.top/embed/{stream_id}")
        urls.append(f"https://ppv.to/embed/{stream_id}")
    else:
        urls.append(f"https://ppv.to/embed/{stream_id}")
        urls.append(f"https://playembed.top/embed/{stream_id}")

    headers = {
        "user-agent": "Mozilla/5.0",
        "referer": f"https://ppv.to/live/{stream_id}"
    }

    # Try all embed URLs
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
        except:
            continue

        if r.status_code == 200:
            playlist = extract_playlist_url(r.text)
            if playlist:
                # 🔥 Redirect langsung ke final m3u8
                return redirect(playlist, code=302)

    return jsonify({"error": "Playlist not found"}), 404


@app.route("/")
def home():
    return "PPV Python API is running!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
