#!/usr/bin/env python3
import requests
from datetime import datetime
import base64
import json

# API credentials
USERNAME = "rUHkYRvkqy9sQhDpKC6nX2QI"
PASSWORD = "m3ByXQkl97YuKZqxlT56Tjn4"
BASE_URL = "https://api.theracingapi.com"

# Create auth header
credentials = f"{USERNAME}:{PASSWORD}"
encoded = base64.b64encode(credentials.encode()).decode()
headers = {"Authorization": f"Basic {encoded}"}

# Today's date
today = datetime.now().strftime("%Y-%m-%d")
print(f"Testing correct API endpoints for: {today}")

# 1. List all meets
print("\n1. Listing all meets:")
print("=" * 60)
meets_url = f"{BASE_URL}/v1/north-america/meets"
try:
    response = requests.get(meets_url, headers=headers)
    print(f"URL: {meets_url}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        meets = response.json()
        print(f"Total meets: {len(meets)}")
        
        # Find Fair Meadows meets
        fm_meets = [m for m in meets if 'FM' in str(m.get('track_code', '')).upper() or 'fair meadows' in str(m.get('track_name', '')).lower()]
        print(f"\nFair Meadows meets found: {len(fm_meets)}")
        
        if fm_meets:
            for meet in fm_meets[:3]:  # Show first 3
                print(f"\nMeet ID: {meet.get('id')}")
                print(f"Track: {meet.get('track_name')} ({meet.get('track_code')})")
                print(f"Date: {meet.get('date')}")
                print(f"Races: {meet.get('race_count', 'N/A')}")
                
                # Get entries for this meet
                if meet.get('id'):
                    meet_id = meet['id']
                    print(f"\n2. Getting entries for meet {meet_id}:")
                    entries_url = f"{BASE_URL}/v1/north-america/meets/{meet_id}/entries"
                    entries_resp = requests.get(entries_url, headers=headers)
                    print(f"Entries status: {entries_resp.status_code}")
                    
                    if entries_resp.status_code == 200:
                        entries = entries_resp.json()
                        print(f"Total entries: {len(entries)}")
                        if entries:
                            print(f"First entry: {json.dumps(entries[0], indent=2)[:200]}...")
                    
                    # Get results for this meet
                    print(f"\n3. Getting results for meet {meet_id}:")
                    results_url = f"{BASE_URL}/v1/north-america/meets/{meet_id}/results"
                    results_resp = requests.get(results_url, headers=headers)
                    print(f"Results status: {results_resp.status_code}")
                    
                    if results_resp.status_code == 200:
                        results = results_resp.json()
                        print(f"Total results: {len(results)}")
        else:
            # Show all available tracks
            print("\nNo Fair Meadows meets found. Available tracks:")
            track_codes = set()
            for meet in meets[:20]:  # Show first 20
                track_info = f"{meet.get('track_name')} ({meet.get('track_code')})"
                track_codes.add(track_info)
            
            for track in sorted(track_codes):
                print(f"- {track}")
                
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")