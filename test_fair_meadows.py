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
print(f"Checking Fair Meadows data for: {today}")

# First, let's get all tracks
tracks_url = f"{BASE_URL}/v1/tracks"
print(f"\nFetching tracks from: {tracks_url}")

try:
    response = requests.get(tracks_url, headers=headers)
    print(f"Tracks status code: {response.status_code}")
    
    if response.status_code == 200:
        tracks = response.json()
        print(f"Total tracks: {len(tracks)}")
        for track in tracks:
            print(f"- {track.get('name', 'Unknown')} ({track.get('code', 'N/A')})")
    else:
        print(f"Error getting tracks: {response.text}")
        
except Exception as e:
    print(f"Error fetching tracks: {e}")

# Now check Fair Meadows races for today
races_url = f"{BASE_URL}/v1/races/FM/{today}"
print(f"\nFetching Fair Meadows races from: {races_url}")

try:
    response = requests.get(races_url, headers=headers)
    print(f"Races status code: {response.status_code}")
    
    if response.status_code == 200:
        races = response.json()
        print(f"Fair Meadows races today: {len(races)}")
        
        for i, race in enumerate(races[:3]):  # Show first 3 races
            print(f"\nRace {i+1}:")
            print(json.dumps(race, indent=2))
            
        # Check entries for first race
        if races:
            race_number = races[0].get('race_number', 1)
            entries_url = f"{BASE_URL}/v1/entries/FM/{today}/{race_number}"
            print(f"\nFetching entries for race {race_number} from: {entries_url}")
            
            entries_response = requests.get(entries_url, headers=headers)
            print(f"Entries status code: {entries_response.status_code}")
            
            if entries_response.status_code == 200:
                entries = entries_response.json()
                print(f"Entries in race {race_number}: {len(entries)}")
            else:
                print(f"Error getting entries: {entries_response.text}")
                
    else:
        print(f"Error response: {response.text}")
        
except Exception as e:
    print(f"Error connecting to API: {e}")