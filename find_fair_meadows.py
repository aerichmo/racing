#!/usr/bin/env python3
import requests
from datetime import datetime, timedelta
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

print("Searching for Fair Meadows track...")

# Try different date ranges
for days_offset in range(0, 30):  # Check next 30 days
    date_to_check = (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")
    
    meets_url = f"{BASE_URL}/v1/north-america/meets?date={date_to_check}"
    try:
        response = requests.get(meets_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            meets = data.get('meets', [])
            
            for meet in meets:
                track_name = meet.get('track_name', '').lower()
                track_id = meet.get('track_id', '')
                
                # Check for Fair Meadows or FM
                if 'fair' in track_name or 'meadows' in track_name or track_id == 'FM':
                    print(f"\nFOUND Fair Meadows!")
                    print(f"Date: {meet.get('date')}")
                    print(f"Track ID: {track_id}")
                    print(f"Track Name: {meet.get('track_name')}")
                    print(f"Meet ID: {meet.get('meet_id')}")
                    
                    # Get entries for this meet
                    meet_id = meet.get('meet_id')
                    if meet_id:
                        entries_url = f"{BASE_URL}/v1/north-america/meets/{meet_id}/entries"
                        entries_resp = requests.get(entries_url, headers=headers)
                        if entries_resp.status_code == 200:
                            entries_data = entries_resp.json()
                            print(f"Total entries: {len(entries_data)}")
                            if entries_data:
                                print(f"Sample entry: {json.dumps(entries_data[0], indent=2)[:400]}...")
                    break
            else:
                continue
            break
    except Exception as e:
        print(f"Error checking {date_to_check}: {e}")

# Also list all unique track names/IDs we've seen
print("\n\nAll tracks found:")
all_tracks = set()

for days_offset in range(0, 7):  # Check next 7 days
    date_to_check = (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")
    
    meets_url = f"{BASE_URL}/v1/north-america/meets?date={date_to_check}"
    try:
        response = requests.get(meets_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            meets = data.get('meets', [])
            
            for meet in meets:
                track_info = f"{meet.get('track_name')} ({meet.get('track_id')})"
                all_tracks.add(track_info)
                
    except:
        pass

for track in sorted(all_tracks):
    print(f"- {track}")