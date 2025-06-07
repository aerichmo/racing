#!/usr/bin/env python3
"""Debug the actual racing API to find where entries are stored"""

import asyncio
import httpx
import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from racing_api import RacingAPIClient
from datetime import date

async def debug_fair_meadows_structure():
    """Debug the actual API response structure"""
    
    print("🔍 Debugging Fair Meadows API Structure")
    print("="*60)
    
    # Initialize API client
    api_client = RacingAPIClient()
    today = date.today()
    
    try:
        # Get races for Fair Meadows
        print("\n1️⃣ Getting Fair Meadows races...")
        races_data = await api_client.get_races_by_date('FM', today)
        
        # Save full response for analysis
        with open('fm_api_response.json', 'w') as f:
            json.dump(races_data, f, indent=2)
        print("   ✅ Full API response saved to fm_api_response.json")
        
        # Analyze response structure
        print(f"\n2️⃣ Response structure:")
        print(f"   Top-level keys: {list(races_data.keys())}")
        
        if 'races' in races_data:
            races = races_data['races']
            print(f"   Number of races: {len(races)}")
            
            if races:
                # Analyze first race structure
                first_race = races[0]
                print(f"\n3️⃣ First race structure:")
                print(f"   Keys: {list(first_race.keys())[:10]}...")  # First 10 keys
                
                # Look for entry-related fields
                print(f"\n4️⃣ Looking for entry/horse data in race object:")
                entry_fields = ['entries', 'horses', 'runners', 'starters', 'competitors', 'field']
                
                for field in entry_fields:
                    if field in first_race:
                        print(f"   ✅ Found '{field}' field!")
                        field_data = first_race[field]
                        if isinstance(field_data, list):
                            print(f"      - Type: list, Length: {len(field_data)}")
                            if field_data:
                                print(f"      - First item type: {type(field_data[0])}")
                                if isinstance(field_data[0], dict):
                                    print(f"      - First item keys: {list(field_data[0].keys())[:5]}...")
                        else:
                            print(f"      - Type: {type(field_data)}")
                
                # Check all fields for lists that might be entries
                print(f"\n5️⃣ All list fields in race object:")
                for key, value in first_race.items():
                    if isinstance(value, list) and len(value) > 0:
                        print(f"   - {key}: list of {len(value)} items")
                        if isinstance(value[0], dict) and len(value[0]) > 5:
                            # Might be entries if it's a list of complex objects
                            print(f"     → First item has {len(value[0])} fields")
                            # Check for horse-related fields
                            first_item = value[0]
                            horse_fields = ['horse', 'name', 'jockey', 'trainer', 'number', 'post']
                            matching_fields = [f for f in horse_fields if any(f in k.lower() for k in first_item.keys())]
                            if matching_fields:
                                print(f"     → Likely entries! Contains: {matching_fields}")
                                print(f"     → Sample keys: {list(first_item.keys())[:10]}")
        
        # Test get_race_entries method
        print(f"\n6️⃣ Testing get_race_entries method:")
        if 'races' in races_data and races_data['races']:
            for i in range(min(3, len(races_data['races']))):
                race_num = i + 1
                entries_response = await api_client.get_race_entries('FM', today, race_num)
                print(f"   Race {race_num}: {len(entries_response.get('entries', []))} entries")
                
                if entries_response.get('entries'):
                    first_entry = entries_response['entries'][0]
                    print(f"      → First entry keys: {list(first_entry.keys())[:5]}...")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check for API credentials
    if not os.getenv("RACING_API_USERNAME"):
        print("⚠️  No API credentials found in environment")
        print("   Setting test credentials...")
        os.environ["RACING_API_USERNAME"] = "test"
        os.environ["RACING_API_PASSWORD"] = "test"
    
    asyncio.run(debug_fair_meadows_structure())