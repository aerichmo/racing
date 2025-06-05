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
print(f"Testing API endpoints for: {today}")

# Test endpoints based on user guidance: meets, entries, results
test_endpoints = [
    # Meets endpoints
    f"{BASE_URL}/meets",
    f"{BASE_URL}/meets/FM",
    f"{BASE_URL}/meets/{today}",
    f"{BASE_URL}/meets/FM/{today}",
    
    # Entries endpoints
    f"{BASE_URL}/entries",
    f"{BASE_URL}/entries/FM",
    f"{BASE_URL}/entries/{today}",
    f"{BASE_URL}/entries/FM/{today}",
    
    # Results endpoints
    f"{BASE_URL}/results",
    f"{BASE_URL}/results/FM",
    f"{BASE_URL}/results/{today}",
    f"{BASE_URL}/results/FM/{today}",
    
    # With v1 prefix
    f"{BASE_URL}/v1/meets",
    f"{BASE_URL}/v1/meets/FM",
    f"{BASE_URL}/v1/meets/{today}",
    f"{BASE_URL}/v1/meets/FM/{today}",
    f"{BASE_URL}/v1/entries",
    f"{BASE_URL}/v1/entries/FM",
    f"{BASE_URL}/v1/entries/{today}",
    f"{BASE_URL}/v1/entries/FM/{today}",
    f"{BASE_URL}/v1/results",
    f"{BASE_URL}/v1/results/FM",
    f"{BASE_URL}/v1/results/{today}",
    f"{BASE_URL}/v1/results/FM/{today}",
]

print("\nTesting meets, entries, and results endpoints:")
print("=" * 60)

for url in test_endpoints:
    try:
        print(f"\nTesting: {url}")
        response = requests.get(url, headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS! Found working endpoint")
            try:
                data = response.json()
                print(f"Response type: {type(data)}")
                if isinstance(data, list):
                    print(f"List length: {len(data)}")
                    if data:
                        print(f"First item: {json.dumps(data[0], indent=2)[:300]}...")
                elif isinstance(data, dict):
                    print(f"Keys: {list(data.keys())}")
                    print(f"Response preview: {json.dumps(data, indent=2)[:300]}...")
            except:
                print(f"Response (text): {response.text[:300]}...")
                
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")