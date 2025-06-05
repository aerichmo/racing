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
        meets_data = response.json()
        print(f"Response type: {type(meets_data)}")
        
        # Check if it's a list or dict
        if isinstance(meets_data, list):
            meets = meets_data
        elif isinstance(meets_data, dict):
            # Maybe the meets are in a specific key
            print(f"Response keys: {list(meets_data.keys())}")
            meets = meets_data.get('meets', meets_data.get('data', []))
        else:
            meets = []
            
        print(f"Total meets: {len(meets)}")
        
        # Show raw data structure
        if meets:
            print(f"\nFirst meet raw data:")
            print(json.dumps(meets[0] if isinstance(meets[0], dict) else str(meets[0]), indent=2)[:500])
            
            # Try to find Fair Meadows
            for i, meet in enumerate(meets):
                print(f"\nMeet {i+1}:")
                if isinstance(meet, dict):
                    print(f"  Keys: {list(meet.keys())}")
                    for key in ['id', 'track_code', 'track_name', 'date', 'meet_id']:
                        if key in meet:
                            print(f"  {key}: {meet[key]}")
                else:
                    print(f"  Value: {meet}")
                    
                if i >= 3:  # Show first 4
                    break
                    
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()