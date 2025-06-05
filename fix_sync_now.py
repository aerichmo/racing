#!/usr/bin/env python3
import asyncio
import sys
import os
from datetime import date, datetime, time
import requests
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from racing_api import RacingAPIClient
from data_sync import DataSync

async def force_sync_fair_meadows():
    """Force sync Fair Meadows races for today"""
    print("FORCING FAIR MEADOWS SYNC FOR TODAY")
    print("=" * 60)
    
    client = RacingAPIClient()
    today = date.today()
    
    # Get races from API
    print(f"1. Getting races from API for {today}...")
    races_data = await client.get_races_by_date('FM', today)
    races = races_data.get('races', [])
    print(f"Found {len(races)} races in API")
    
    if not races:
        print("❌ No races found in API")
        return
    
    # Show race details
    for race in races:
        print(f"  Race {race['race_number']}: {race['post_time']}")
    
    # Now force sync via production API
    print(f"\n2. Creating manual sync payload...")
    
    # Create the exact data structure needed
    sync_payload = {
        "track_name": "Fair Meadows",
        "track_code": "FM", 
        "races": races,
        "date": today.strftime('%Y-%m-%d')
    }
    
    print(f"Payload: {len(races)} races for Fair Meadows")
    
    # Create endpoint to accept this data
    print(f"\n3. We need to create a manual data insertion endpoint...")
    
    # Get entries for first race to see data structure
    print(f"\n4. Getting entries for race 1...")
    entries_data = await client.get_race_entries('FM', today, 1)
    entries = entries_data.get('entries', [])
    print(f"Found {len(entries)} entries for race 1:")
    
    for entry in entries[:3]:
        print(f"  {entry['post_position']}: {entry['horse_name']} - {entry['jockey_name']}")

if __name__ == "__main__":
    asyncio.run(force_sync_fair_meadows())