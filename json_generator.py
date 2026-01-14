import requests
import json
from datetime import datetime, time, timezone, timedelta
import os
import urllib3
from urllib.parse import urlencode
import random
import string

# Suppress only the InsecureRequestWarning from urllib3 needed for verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURATION ---
BASE_URL = "https://h5.aoneroom.com"
OUTPUT_FILENAME = "matches.json"
LOG_FILENAME = "json_generator_log.txt"

# --- HEADERS ---
HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'origin': 'https://aisports.cc',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://aisports.cc/',
    'sec-ch-ua': '"Not;A=Brand";v="99", "Brave";v="139", "Chromium";v="139"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
}

# --- HELPER FUNCTIONS ---

def log_update(message):
    """Appends a message to the log file with a timestamp."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"[{timestamp}] {message}")
    with open(LOG_FILENAME, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")

def generate_unique_id(length=27):
    """Generates a random 27-character alphanumeric lowercase string."""
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_utc_timestamps_for_day(target_date):
    """Calculates the 24-hour window from 21:00 UTC on the previous day."""
    previous_day = target_date - timedelta(days=1)
    start_dt = datetime.combine(previous_day, time(21, 0), tzinfo=timezone.utc)
    end_dt = datetime.combine(target_date, time(20, 59, 59, 999999), tzinfo=timezone.utc)
    return int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)

def get_api_data(url, params):
    """Generic function to fetch data from the API."""
    try:
        response = requests.get(url, params=params, headers=HEADERS, verify=False, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as err:
        log_update(f"API request failed for {url} with params {params}: {err}")
        return None

def get_match_list_for_day(sport_type, target_date):
    """Fetches a list of all matches for a specific day and sport."""
    start_timestamp, end_timestamp = get_utc_timestamps_for_day(target_date)
    api_url = f"{BASE_URL}/wefeed-h5-bff/live/match-list-v3"
    params = {'status': 0, 'matchType': sport_type, 'startTime': start_timestamp, 'endTime': end_timestamp}
    data = get_api_data(api_url, params)
    if data and data.get('code') == 0:
        match_groups = data.get('data', {}).get('list', [])
        all_matches = []
        if match_groups:
            for group in match_groups:
                if group and 'matchList' in group:
                    all_matches.extend(group['matchList'])
        return all_matches
    return []

def get_match_details(match_id):
    """Fetches full details for a single match ID."""
    api_url = f"{BASE_URL}/wefeed-h5-bff/live/match-detail"
    params = {'id': match_id}
    data = get_api_data(api_url, params)
    return data.get('data') if data and data.get('code') == 0 else None

def transform_details_to_json(details, match_id):
    """Transforms the detailed API response into the desired JSON format."""
    if not details:
        return None

    team1 = details.get('team1', {})
    team2 = details.get('team2', {})
    start_time_ms = int(details.get('startTime', 0))
    
    # Get all stream links
    links = []
    primary_stream = details.get('playPath')
    if primary_stream and primary_stream.startswith('http'):
        links.append(primary_stream)
    
    alternative_streams = details.get('playSource', [])
    if alternative_streams:
        for source in alternative_streams:
            if source.get('path') and source['path'].startswith('http'):
                links.append(source['path'])

    # Format date and time
    utc_dt = datetime.fromtimestamp(start_time_ms / 1000, tz=timezone.utc)
    
    return {
        "id": generate_unique_id(),
        "match_id": match_id,
        "source_name": "Premium",
        "match_title_from_api": f"{team1.get('name', 'N/A')} vs {team2.get('name', 'N/A')}",
        "competition": details.get('league', 'Unknown Competition'),
        "team1": {
            "name": team1.get('name', 'N/A'),
            "logo_url": team1.get('avatar', '')
        },
        "team2": {
            "name": team2.get('name', 'N/A'),
            "logo_url": team2.get('avatar', '')
        },
        "time": utc_dt.strftime('%H:%M'),
        "date": utc_dt.strftime('%d-%m-%Y'),
        "links": links
    }

# --- MAIN WORKFLOW ---
def main():
    """Main function to run the JSON generation process."""
    log_update("--- JSON Generator Workflow Started ---")
    
    all_formatted_matches = []
    processed_ids = set()
    target_date = datetime.now(timezone.utc).date()
    
    log_update(f"Scanning for matches in the 24-hour window ending on {target_date.strftime('%Y-%m-%d')} at 21:00 UTC.")
    
    for sport in ["football", "cricket", "basketball"]:
        log_update(f"Fetching {sport.capitalize()} matches...")
        match_list = get_match_list_for_day(sport, target_date)
        
        if not match_list:
            log_update(f"Found 0 matches for {sport.capitalize()}.")
            continue
            
        log_update(f"Found {len(match_list)} matches for {sport.capitalize()}. Processing...")

        for match_summary in match_list:
            match_id = match_summary.get('id')
            if not match_id or match_id in processed_ids:
                continue
                
            processed_ids.add(match_id)
            details = get_match_details(match_id)
            
            if details:
                formatted = transform_details_to_json(details, match_id)
                if formatted:
                    all_formatted_matches.append(formatted)

    # Sort matches by date and then by time
    all_formatted_matches.sort(key=lambda x: (datetime.strptime(x['date'], '%d-%m-%Y'), x['time']))

    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        json.dump(all_formatted_matches, f, indent=4)
        
    log_update(f"Generated {OUTPUT_FILENAME} with {len(all_formatted_matches)} matches.")
    log_update("--- JSON Generator Workflow Finished ---")

if __name__ == "__main__":
    main()

