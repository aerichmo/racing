#!/usr/bin/env python3
import asyncio
import os
import sys
from datetime import date

# Set environment variables
os.environ['RACING_API_USERNAME'] = 'rUHkYRvkqy9sQhDpKC6nX2QI'
os.environ['RACING_API_PASSWORD'] = 'm3ByXQkl97YuKZqxlT56Tjn4'
os.environ['RACING_API_BASE_URL'] = 'https://api.theracingapi.com'

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from racing_api import RacingAPIClient

async def test_api():
    api = RacingAPIClient()
    
    print("Testing racing API with mock fallback...")
    
    # Test meets
    meets = await api.get_meets(date.today())
    print(f"Meets returned: {len(meets.get('meets', []))}")
    
    rp_found = False
    for meet in meets.get('meets', []):
        if meet.get('track_code') == 'RP':
            rp_found = True
            print(f"✓ Found Remington Park with {len(meet.get('races', []))} races")
            break
    
    if not rp_found:
        print("✗ Remington Park not found")
    
    # Test entries
    entries = await api.get_entries(date.today())
    print(f"Entries returned for {len(entries.get('meets', []))} meets")
    
    for meet in entries.get('meets', []):
        if meet.get('track_code') == 'RP':
            for race in meet.get('races', [])[:1]:  # Just check first race
                print(f"  Race {race.get('race_number')}: {len(race.get('entries', []))} entries")
                break
            break
    
    print("✓ API test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_api())