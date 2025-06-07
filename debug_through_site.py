#!/usr/bin/env python3
"""Debug through the deployed site to understand the issue"""

import asyncio
import httpx
import json

async def debug_through_site():
    """Debug by calling the deployed site's APIs"""
    
    base_url = "https://racing-xqpi.onrender.com"
    
    print("🔍 Debugging Entry Sync Issue Through Site")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Trigger a fresh sync to see debug output
        print("\n1️⃣ Triggering fresh race sync to see API structure...")
        response = await client.post(f"{base_url}/api/sync")
        
        if response.status_code == 200:
            sync_data = response.json()
            debug_lines = sync_data.get('debug', [])
            
            # Extract Fair Meadows specific debug info
            print("\n📋 Fair Meadows Debug Info:")
            fm_lines = [line for line in debug_lines if 'Fair Meadows' in line]
            for line in fm_lines:
                print(f"   {line}")
            
            # Look for race structure info
            print("\n🔍 Race Structure Info:")
            structure_lines = [line for line in debug_lines if 'keys' in line.lower() or 'race_key' in line]
            for line in structure_lines[:5]:
                print(f"   {line}")
        
        # 2. Create a test endpoint to inspect race data
        print("\n2️⃣ Checking current Fair Meadows races...")
        
        # Get races to see what we have
        response = await client.get(f"{base_url}/api/races/2")
        if response.status_code == 200:
            races = response.json()
            print(f"   Found {len(races)} races")
            
            if races:
                first_race = races[0]
                print(f"   First race: Race {first_race['race_number']}")
                print(f"   Horses field: {first_race.get('horses', 'NOT FOUND')}")
        
        # 3. Try to understand the entry sync error
        print("\n3️⃣ Attempting entry sync to capture error details...")
        response = await client.post(f"{base_url}/api/sync-entries")
        
        if response.status_code == 200:
            entry_data = response.json()
            print(f"   Status: {entry_data['status']}")
            print(f"   Entries synced: {entry_data.get('entries_count', 0)}")
            
            if entry_data.get('error'):
                print(f"\n   ❌ Error: {entry_data['error']}")
                
                # Parse the traceback for key information
                if entry_data.get('traceback'):
                    tb_lines = entry_data['traceback'].split('\n')
                    print("\n   📋 Key error details:")
                    
                    # Find the actual error
                    for i, line in enumerate(tb_lines):
                        if 'Error:' in line or 'Exception:' in line:
                            print(f"      {line.strip()}")
                        elif 'File' in line and ('data_sync.py' in line or 'racing_api.py' in line):
                            print(f"      {line.strip()}")
                            # Print the next line which shows the code
                            if i + 1 < len(tb_lines):
                                print(f"      {tb_lines[i+1].strip()}")
        
        # 4. Hypothesis: The races format doesn't have entries at race level
        print("\n4️⃣ Hypothesis Check:")
        print("   The Fair Meadows 'races' format might not include entries")
        print("   at the race level. Entries might need a separate API call")
        print("   or might be in a different structure.")
        
        print("\n💡 Potential Solutions:")
        print("   1. Check if entries are in a nested field we haven't found")
        print("   2. Check if entries require a separate API endpoint")
        print("   3. Check if the meet_id needs to be used differently")
        print("   4. The races might genuinely have no entries yet")

if __name__ == "__main__":
    asyncio.run(debug_through_site())