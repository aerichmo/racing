#!/usr/bin/env python3
import asyncio
import httpx
import os
from datetime import date, datetime, timedelta
import base64

# Set environment variables
os.environ['RACING_API_USERNAME'] = 'rUHkYRvkqy9sQhDpKC6nX2QI'
os.environ['RACING_API_PASSWORD'] = 'm3ByXQkl97YuKZqxlT56Tjn4'
os.environ['RACING_API_BASE_URL'] = 'https://api.theracingapi.com'

async def test_api_dates():
    # Create auth header
    username = os.getenv("RACING_API_USERNAME")
    password = os.getenv("RACING_API_PASSWORD")
    base_url = os.getenv("RACING_API_BASE_URL")
    
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    auth_header = {"Authorization": f"Basic {encoded}"}
    
    print("Testing Racing API with different dates...\n")
    
    # Test various dates
    test_dates = [
        date.today(),  # Today
        date.today() - timedelta(days=1),  # Yesterday
        date.today() - timedelta(days=2),  # 2 days ago
        date.today() - timedelta(days=7),  # 1 week ago
        date.today() - timedelta(days=30),  # 1 month ago
        date(2024, 12, 1),  # Specific past date
        date(2024, 11, 15),  # Another past date
    ]
    
    async with httpx.AsyncClient() as client:
        for test_date in test_dates:
            try:
                url = f"{base_url}/meets/{test_date.strftime('%Y-%m-%d')}"
                response = await client.get(url, headers=auth_header)
                
                if response.status_code == 200:
                    data = response.json()
                    meets = data.get('meets', [])
                    
                    print(f"✓ {test_date}: SUCCESS - {len(meets)} meets found")
                    
                    # Check for Remington Park
                    for meet in meets:
                        if meet.get('track_code') == 'RP' or 'Remington' in meet.get('track_name', ''):
                            print(f"  → Found Remington Park: {meet.get('track_name')} with {len(meet.get('races', []))} races")
                            break
                else:
                    print(f"✗ {test_date}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"✗ {test_date}: ERROR - {str(e)}")
    
    print("\nTesting entries endpoint...")
    
    # Test entries for a successful date
    successful_date = date(2024, 12, 1)
    try:
        url = f"{base_url}/entries/{successful_date.strftime('%Y-%m-%d')}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=auth_header)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Entries endpoint works for {successful_date}")
                
                # Check for Remington Park entries
                for meet in data.get('meets', []):
                    if meet.get('track_code') == 'RP':
                        print(f"  → Found Remington Park entries")
                        for race in meet.get('races', [])[:2]:  # Show first 2 races
                            print(f"     Race {race.get('race_number')}: {len(race.get('entries', []))} entries")
            else:
                print(f"✗ Entries endpoint failed: HTTP {response.status_code}")
                
    except Exception as e:
        print(f"✗ Entries endpoint error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_api_dates())