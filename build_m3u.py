#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from datetime import datetime, timezone
from urllib.request import urlopen, Request

JSON_URL = "https://raw.githubusercontent.com/drnewske/areallybadideabuttidonthateitijusthateitsomuch/refs/heads/main/matches.json"
OUT_FILE = "matches.m3u"

# Logo fallback (boleh ganti ke logo kamu)
FALLBACK_LOGO = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Tennis_icon.svg/512px-Tennis_icon.svg.png"

UA = "Mozilla/5.0 (compatible; OgieTV-M3U-Bot/1.0)"

def safe(s: str) -> str:
    return (s or "").strip()

def fetch_json(url: str) -> list:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=30) as r:
        data = r.read().decode("utf-8", errors="replace")
    return json.loads(data)

def parse_iso(dt_str: str) -> str:
    # Keep original if parsing fails
    if not dt_str:
        return ""
    try:
        # Example: 2026-01-11T23:00:00
        dt = datetime.fromisoformat(dt_str)
        # Convert to ISO w/ Z if naive
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return dt_str

def main():
    try:
        items = fetch_json(JSON_URL)
    except Exception as e:
        print(f"Failed to fetch/parse JSON: {e}", file=sys.stderr)
        sys.exit(1)

    lines = []
    lines.append("#EXTM3U")

    for it in items:
        mid = safe(it.get("id"))
        title = safe(it.get("title")) or mid
        sport = safe(it.get("sport")) or "sports"
        is_live = bool(it.get("isLive", False))
        kickoff = safe(it.get("kickOff"))
        kickoff_txt = parse_iso(kickoff)

        # team logos sometimes empty; prefer team1/team2 logo if exists
        team1_logo = safe((it.get("team1") or {}).get("logo"))
        team2_logo = safe((it.get("team2") or {}).get("logo"))
        tvg_logo = team1_logo or team2_logo or FALLBACK_LOGO

        # group-title by sport + live flag
        grp = f"{sport.upper()} - {'LIVE' if is_live else 'UPCOMING'}"

        # pick best link: prefer hd=True then language=English, else first
        links = it.get("links") or []
        if not links:
            continue

        def score_link(L):
            sc = 0
            if L.get("hd") is True:
                sc += 10
            if safe(L.get("language")).lower() == "english":
                sc += 3
            return sc

        best = sorted(links, key=score_link, reverse=True)[0]
        url = safe(best.get("url"))
        lang = safe(best.get("language"))
        hd = best.get("hd", False)

        # display name
        suffix = []
        if lang:
            suffix.append(lang)
        if hd:
            suffix.append("HD")
        if kickoff_txt:
            suffix.append(kickoff_txt)
        name = title + (f" ({' • '.join(suffix)})" if suffix else "")

        # M3U entry
        # Note: URL here is embed page URL (not direct HLS).
        extinf = (
            f'#EXTINF:-1 tvg-id="{mid}" tvg-name="{title}" '
            f'group-title="{grp}" tvg-logo="{tvg_logo}",{name}'
        )
        lines.append(extinf)
        lines.append(url)

    content = "\n".join(lines).strip() + "\n"
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"OK: wrote {OUT_FILE} with {max(0, len(lines)-1)//2} items")

if __name__ == "__main__":
    main()
