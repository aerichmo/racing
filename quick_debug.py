#!/usr/bin/env python3
"""Quick debug to find why entries aren't syncing"""

import asyncio
import httpx
import json

async def quick_debug():
    base_url = "https://racing-xqpi.onrender.com"
    
    print("🔍 Quick Debug - Entry Sync Issue")
    print("="*50)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Check current state
        print("\n1️⃣ Current Database State:")
        response = await client.get(f"{base_url}/api/debug/races")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total races: {data['total_races_in_db']}")
            print(f"   Races today: {data['races_today']}")
            if data['today_races_detail']:
                fm_races = [r for r in data['today_races_detail'] if r['track_id'] == 2]
                print(f"   Fair Meadows races today: {len(fm_races)}")
        
        # 2. Check Fair Meadows races
        print("\n2️⃣ Fair Meadows Race Details:")
        response = await client.get(f"{base_url}/api/races/2")
        if response.status_code == 200:
            races = response.json()
            print(f"   Total races returned: {len(races)}")
            if races:
                print(f"   First race: Race {races[0]['race_number']} at {races[0]['race_time']}")
                print(f"   Horses in first race: {races[0]['horses']}")
        
        # 3. Try entry sync
        print("\n3️⃣ Attempting Entry Sync:")
        response = await client.post(f"{base_url}/api/sync-entries")
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data['status']}")
            print(f"   Entries count: {data.get('entries_count', 0)}")
            
            if data.get('error'):
                print(f"   ❌ Error: {data['error']}")
                if data.get('traceback'):
                    print("\n   📋 Key error lines:")
                    lines = data['traceback'].split('\n')
                    for line in lines:
                        if 'File' in line and 'src/' in line:
                            print(f"      {line.strip()}")
                        elif 'Error' in line or 'Exception' in line:
                            print(f"      {line.strip()}")
        else:
            print(f"   ❌ Entry sync returned status: {response.status_code}")
            print(f"   Response: {response.text}")
        
        # 4. Manual API test
        print("\n4️⃣ Testing Raw API Response Format:")
        print("   Checking what Fair Meadows API actually returns...")
        
        # We need to understand the exact format
        response = await client.post(f"{base_url}/api/sync")
        if response.status_code == 200:
            data = response.json()
            debug_info = data.get('debug', [])
            
            # Look for Fair Meadows specific debug info
            for line in debug_info:
                if 'Fair Meadows' in line and ('keys' in line or 'race_key' in line):
                    print(f"   {line}")
            
            # Check if races have entries field
            print("\n   🔍 Looking for race structure info...")
            for line in debug_info:
                if 'First race keys' in line:
                    print(f"   {line}")

if __name__ == "__main__":
    asyncio.run(quick_debug())