#!/usr/bin/env python3
"""Debug why entry sync isn't working"""

import asyncio
import httpx
import json

async def debug_entry_sync():
    base_url = "https://racing-xqpi.onrender.com"
    
    print("🔍 Debugging Entry Sync Issue")
    print("="*50)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check what get_race_entries returns for each race
        print("\n📋 Testing get_race_entries for each race...")
        
        # We need to test this through our deployed system
        # Let's create a test endpoint to debug this
        
        # For now, let's check the sync-entries response with more detail
        print("\n🔄 Running entry sync with detailed monitoring...")
        
        response = await client.post(f"{base_url}/api/sync-entries")
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Entries count: {data.get('entries_count', 0)}")
            
            if data.get('error'):
                print(f"Error: {data['error']}")
                if data.get('traceback'):
                    print("\nTraceback:")
                    print(data['traceback'])
        
        # Let's also check the race structure to verify runners are there
        print("\n🏇 Checking race structure...")
        response = await client.get(f"{base_url}/api/debug/race-structure")
        if response.status_code == 200:
            data = response.json()
            if data.get('has_runners'):
                print(f"✅ Races have runners: {data.get('runners_count')} in first race")
                print(f"Runner fields: {data.get('runner_fields', [])[:10]}...")
            else:
                print("❌ No runners found in race structure")

if __name__ == "__main__":
    asyncio.run(debug_entry_sync())