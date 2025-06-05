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

# Test different possible API structures
test_urls = [
    # Original structure
    f"{BASE_URL}/v1/tracks",
    f"{BASE_URL}/v1/races/FM/{today}",
    
    # Without v1
    f"{BASE_URL}/tracks",
    f"{BASE_URL}/races/FM/{today}",
    
    # With api prefix
    f"{BASE_URL}/api/v1/tracks",
    f"{BASE_URL}/api/v1/races/FM/{today}",
    f"{BASE_URL}/api/tracks",
    f"{BASE_URL}/api/races/FM/{today}",
    
    # Root endpoint
    BASE_URL,
    f"{BASE_URL}/",
    f"{BASE_URL}/api",
    f"{BASE_URL}/v1",
    
    # Different date format
    f"{BASE_URL}/v1/races/FM/{today.replace('-', '')}",
    f"{BASE_URL}/v1/races/FM/{today.replace('-', '/')}",
]

print("\nTesting various API endpoints:")
print("=" * 60)

for url in test_urls:
    try:
        print(f"\nTesting: {url}")
        response = requests.get(url, headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS! Found working endpoint")
            try:
                data = response.json()
                print(f"Response preview: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"Response (text): {response.text[:200]}...")
        elif response.status_code == 401:
            print("Authentication failed - check credentials")
        elif response.status_code == 404:
            print("Not found")
        else:
            print(f"Error: {response.text[:100]}...")
            
    except requests.exceptions.Timeout:
        print("Timeout - endpoint not responding")
    except requests.exceptions.ConnectionError:
        print("Connection error - could not reach server")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")

# Try without authentication
print("\n\nTrying without authentication:")
print("=" * 60)
for url in [BASE_URL, f"{BASE_URL}/", f"{BASE_URL}/api", f"{BASE_URL}/docs"]:
    try:
        print(f"\nTesting: {url}")
        response = requests.get(url, timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response preview: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {str(e)}")