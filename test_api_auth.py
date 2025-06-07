#!/usr/bin/env python3
import asyncio
import httpx
import os
import base64

# Set environment variables
os.environ['RACING_API_USERNAME'] = 'rUHkYRvkqy9sQhDpKC6nX2QI'
os.environ['RACING_API_PASSWORD'] = 'm3ByXQkl97YuKZqxlT56Tjn4'
os.environ['RACING_API_BASE_URL'] = 'https://api.theracingapi.com'

async def test_api_auth():
    username = os.getenv("RACING_API_USERNAME")
    password = os.getenv("RACING_API_PASSWORD")
    base_url = os.getenv("RACING_API_BASE_URL")
    
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    auth_header = {"Authorization": f"Basic {encoded}"}
    
    print(f"Testing API Authentication...")
    print(f"Base URL: {base_url}")
    print(f"Username: {username}")
    print(f"Auth header: Basic {encoded[:10]}...")
    
    async with httpx.AsyncClient() as client:
        # Test root endpoint
        print("\n1. Testing root endpoint...")
        try:
            response = await client.get(base_url, headers=auth_header)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {response.text[:200]}...")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test without auth
        print("\n2. Testing meets endpoint without auth...")
        try:
            response = await client.get(f"{base_url}/meets/2024-01-01")
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test with auth
        print("\n3. Testing meets endpoint with auth...")
        try:
            response = await client.get(f"{base_url}/meets/2024-01-01", headers=auth_header)
            print(f"   Status: {response.status_code}")
            if response.headers:
                print(f"   Headers: {dict(response.headers)}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Try different date formats
        print("\n4. Testing different date formats...")
        date_formats = ["2024-01-01", "20240101", "01-01-2024", "01/01/2024"]
        for fmt in date_formats:
            try:
                response = await client.get(f"{base_url}/meets/{fmt}", headers=auth_header)
                print(f"   {fmt}: Status {response.status_code}")
            except Exception as e:
                print(f"   {fmt}: Error")

if __name__ == "__main__":
    asyncio.run(test_api_auth())