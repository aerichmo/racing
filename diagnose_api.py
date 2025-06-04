#!/usr/bin/env python3
import requests
import base64
from datetime import datetime

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

print("=== API Endpoint Testing ===")
print(f"Testing date: {today}")
print(f"Base URL: {BASE_URL}")
print(f"Auth: Basic {encoded[:20]}...")

# List of endpoints to test
endpoints = [
    # Version 1 endpoints
    "/v1/tracks",
    f"/v1/races/FM/{today}",
    f"/v1/meets/{today}",
    f"/v1/entries/{today}",
    
    # No version endpoints
    "/tracks",
    f"/races/FM/{today}",
    f"/meets/{today}",
    f"/entries/{today}",
    
    # Alternative patterns
    "/api/v1/tracks",
    f"/api/races/{today}",
    f"/api/tracks/FM/races/{today}",
    
    # Root endpoint
    "/",
    "/api",
    "/v1"
]

for endpoint in endpoints:
    url = BASE_URL + endpoint
    print(f"\nTesting: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  SUCCESS! Response preview: {str(response.text)[:200]}...")
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"  Data: List with {len(data)} items")
                    elif isinstance(data, dict):
                        print(f"  Data: Dict with keys: {list(data.keys())[:5]}")
                except:
                    pass
        elif response.status_code == 401:
            print("  Authentication failed")
        elif response.status_code == 404:
            print("  Not found")
        else:
            print(f"  Error: {response.text[:100]}")
            
    except requests.exceptions.Timeout:
        print("  TIMEOUT")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {str(e)}")

print("\n=== Testing without auth ===")
# Try without auth to see if we get different error
test_url = BASE_URL + "/v1/tracks"
response = requests.get(test_url, timeout=5)
print(f"No auth status: {response.status_code}")
if response.status_code != 404:
    print(f"Response: {response.text[:200]}")