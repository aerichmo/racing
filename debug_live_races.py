#!/usr/bin/env python3
import asyncio
import sys
import os
from datetime import date
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from racing_api import RacingAPIClient

async def debug_live_races():
    """Debug why Fair Meadows live races aren't showing"""
    client = RacingAPIClient()
    
    print("DEBUGGING LIVE FAIR MEADOWS RACES")
    print("=" * 60)
    
    today = date.today()
    print(f"Today's date: {today}")
    
    # 1. Check meets for TODAY
    print(f"\n1. Checking meets for TODAY ({today}):")
    try:
        meets_today = await client.get_meets(today.strftime('%Y-%m-%d'))
        print(f"Total meets today: {len(meets_today)}")
        
        # Look for Fair Meadows variants
        fair_meadows_variants = []
        for meet in meets_today:
            track_name = meet.get('track_name', '').lower()
            track_id = meet.get('track_id', '')
            
            if ('fair' in track_name or 'meadows' in track_name or 
                track_id in ['FM', 'FMT', 'FMN']):
                fair_meadows_variants.append(meet)
                print(f"\nFOUND: {meet}")
        
        if not fair_meadows_variants:
            print("❌ NO Fair Meadows meets found for today")
            
            # Show all tracks today
            print(f"\nAll tracks racing today:")
            for meet in meets_today:
                print(f"  - {meet.get('track_name')} ({meet.get('track_id')})")
        
    except Exception as e:
        print(f"Error getting today's meets: {e}")
    
    # 2. Check meets for ALL upcoming dates
    print(f"\n2. Checking Fair Meadows meets in next 7 days:")
    try:
        from datetime import timedelta
        
        fair_meadows_meets = []
        for days_ahead in range(0, 8):  # Today + next 7 days
            check_date = today + timedelta(days=days_ahead)
            meets = await client.get_meets(check_date.strftime('%Y-%m-%d'))
            
            for meet in meets:
                track_name = meet.get('track_name', '').lower()
                track_id = meet.get('track_id', '')
                
                if ('fair' in track_name and 'meadows' in track_name) or track_id in ['FMT', 'FMN']:
                    fair_meadows_meets.append((check_date, meet))
                    print(f"  {check_date}: {meet.get('track_name')} ({meet.get('track_id')})")
        
        if not fair_meadows_meets:
            print("❌ NO Fair Meadows meets found in next 7 days")
        
    except Exception as e:
        print(f"Error checking upcoming meets: {e}")
    
    # 3. Try different track IDs for today
    print(f"\n3. Testing different track IDs for Fair Meadows today:")
    possible_track_ids = ['FMT', 'FM', 'FMN', 'FAI', 'FAIR']
    
    for track_id in possible_track_ids:
        try:
            print(f"\nTrying track ID: {track_id}")
            races_data = await client.get_races_by_date(track_id, today)
            races = races_data.get('races', [])
            print(f"  Races found: {len(races)}")
            
            if races:
                print(f"  ✅ SUCCESS! Found {len(races)} races for {track_id}")
                for race in races[:2]:
                    print(f"    Race {race.get('race_number')}: {race.get('post_time')}")
                break
        except Exception as e:
            print(f"  ❌ Error for {track_id}: {e}")
    
    # 4. Raw API check without our mapping
    print(f"\n4. Raw API check for today:")
    try:
        meets_today = await client.get_meets(today.strftime('%Y-%m-%d'))
        print(f"Raw meets response contains {len(meets_today)} meets")
        
        # Show all track IDs
        track_ids = set()
        for meet in meets_today:
            track_ids.add(f"{meet.get('track_name')} ({meet.get('track_id')})")
        
        print("All track IDs racing today:")
        for track in sorted(track_ids):
            print(f"  - {track}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_live_races())