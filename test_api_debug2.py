#!/usr/bin/env python3
import asyncio
import sys
import os
from datetime import date
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from racing_api import RacingAPIClient

async def test_api():
    client = RacingAPIClient()
    
    print("Debugging API issue...")
    print("=" * 60)
    
    # Get meets for next week to find Fair Meadows
    print("\nChecking Fair Meadows meet on June 11:")
    try:
        meets = await client.get_meets('2025-06-11')
        fm_meets = [m for m in meets if m.get('track_id') == 'FMT']
        
        if fm_meets:
            meet = fm_meets[0]
            print(f"Meet found: {meet}")
            
            # Get entries directly
            print(f"\nGetting entries for meet ID: {meet['meet_id']}")
            entries = await client.get_meet_entries(meet['meet_id'])
            
            print(f"Entries type: {type(entries)}")
            if isinstance(entries, list):
                print(f"Number of entries: {len(entries)}")
                if entries:
                    print(f"First entry: {json.dumps(entries[0], indent=2)}")
            else:
                print(f"Entries response: {entries}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())