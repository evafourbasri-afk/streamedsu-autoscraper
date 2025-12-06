name: FAST StreamedSU Scraper

on:
  workflow_dispatch:

jobs:
  scrape_fast:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps + Playwright Chromium ONLY
        run: |
          python -m pip install --upgrade pip
          pip install playwright requests
          python -m playwright install chromium
          python -m playwright install-deps

      - name: Run FAST Scraper
        run: python streamed_fast.py

      - name: Upload FAST Playlist
        uses: actions/upload-artifact@v4
        with:
          name: StreamedSU_FAST
          path: StreamedSU_FAST.m3u8
