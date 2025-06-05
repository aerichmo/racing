#!/usr/bin/env python3
import asyncio
import sys
import os
from datetime import date

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from racing_api import RacingAPIClient

async def test_api():
    client = RacingAPIClient()
    
    print("Testing updated Racing API client...")
    print("=" * 60)
    
    # Test 1: Get meets for today
    today = date.today()
    print(f"\n1. Getting meets for today ({today}):")
    try:
        meets = await client.get_meets(today.strftime('%Y-%m-%d'))
        print(f"Found {len(meets)} meets")
        
        for meet in meets:
            if 'fair' in meet.get('track_name', '').lower() or meet.get('track_id') == 'FMT':
                print(f"\nFair Meadows meet found!")
                print(f"  Track: {meet.get('track_name')} ({meet.get('track_id')})")
                print(f"  Date: {meet.get('date')}")
                print(f"  Meet ID: {meet.get('meet_id')}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Get races for Fair Meadows
    print(f"\n2. Getting races for Fair Meadows (FM code):")
    try:
        races_data = await client.get_races_by_date('FM', today)
        races = races_data.get('races', [])
        print(f"Found {len(races)} races")
        
        if races:
            for race in races[:3]:  # Show first 3
                print(f"\n  Race {race.get('race_number')}:")
                print(f"    Post time: {race.get('post_time')}")
                print(f"    Distance: {race.get('distance')}")
                print(f"    Type: {race.get('race_type')}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Get entries for a race
    if races:
        race_num = races[0].get('race_number', 1)
        print(f"\n3. Getting entries for Fair Meadows Race {race_num}:")
        try:
            entries_data = await client.get_race_entries('FM', today, race_num)
            entries = entries_data.get('entries', [])
            print(f"Found {len(entries)} entries")
            
            if entries:
                for entry in entries[:3]:  # Show first 3
                    print(f"\n  Horse: {entry.get('horse_name')}")
                    print(f"    Post: {entry.get('post_position')}")
                    print(f"    Jockey: {entry.get('jockey_name')}")
                    print(f"    Trainer: {entry.get('trainer_name')}")
                    print(f"    ML Odds: {entry.get('morning_line_odds')}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api())