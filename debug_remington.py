#!/usr/bin/env python3
import asyncio
import sys
import os
from datetime import date, datetime
from sqlalchemy.orm import Session

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql://mob1e_user:dU3nupu3FgdqClieo5JZWoZ2eL1KSMZB@dpg-d0lk5oogjchc73f5ieqg-a.oregon-postgres.render.com/mob1e'
os.environ['RACING_API_USERNAME'] = 'rUHkYRvkqy9sQhDpKC6nX2QI'
os.environ['RACING_API_PASSWORD'] = 'm3ByXQkl97YuKZqxlT56Tjn4'
os.environ['RACING_API_BASE_URL'] = 'https://api.theracingapi.com'

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import get_db, Track, Race, Bet, RaceEntry
from racing_api import RacingAPIClient
from data_sync import DataSync

async def debug_remington():
    # Get database session
    db = next(get_db())
    
    print("=== Checking Database for Remington Park ===")
    
    # Check if Remington Park exists in database
    rp = db.query(Track).filter(Track.name == "Remington Park").first()
    if rp:
        print(f"✓ Remington Park found in DB: ID={rp.id}, Code={rp.code}")
    else:
        print("✗ Remington Park NOT found in database")
        return
    
    # Check for races today
    today = date.today()
    races = db.query(Race).filter(
        Race.track_id == rp.id,
        Race.race_date == today
    ).all()
    
    print(f"\n=== Races for Remington Park on {today} ===")
    print(f"Found {len(races)} races")
    
    for race in races[:3]:  # Show first 3 races
        print(f"- Race {race.race_number}: {race.race_time}")
        
        # Check entries
        entries = db.query(RaceEntry).filter(RaceEntry.race_id == race.id).count()
        print(f"  Entries: {entries}")
        
        # Check bets
        bets = db.query(Bet).filter(Bet.race_id == race.id).count()
        print(f"  Bets: {bets}")
    
    print("\n=== Testing API Connection ===")
    
    # Test API
    api_client = RacingAPIClient()
    
    try:
        print(f"\nFetching meets for {today}...")
        meets_data = await api_client.get_meets(today)
        
        print(f"API returned {len(meets_data.get('meets', []))} meets")
        
        # Look for Remington Park in API response
        rp_found = False
        for meet in meets_data.get('meets', []):
            if meet.get('track_code') == 'RP' or 'Remington' in meet.get('track_name', ''):
                rp_found = True
                print(f"\n✓ Found Remington Park in API response:")
                print(f"  Track Code: {meet.get('track_code')}")
                print(f"  Track Name: {meet.get('track_name')}")
                print(f"  Races: {len(meet.get('races', []))}")
                break
        
        if not rp_found:
            print("\n✗ Remington Park NOT found in API response")
            print("Available tracks:")
            for meet in meets_data.get('meets', []):
                print(f"  - {meet.get('track_name')} ({meet.get('track_code')})")
    
    except Exception as e:
        print(f"Error calling API: {e}")
    
    print("\n=== Testing Data Sync ===")
    
    # Test data sync
    data_sync = DataSync()
    
    try:
        print("Running initial sync...")
        await data_sync.sync_initial_data(db)
        print("✓ Initial sync completed")
        
        # Check races again after sync
        races_after = db.query(Race).filter(
            Race.track_id == rp.id,
            Race.race_date == today
        ).count()
        
        print(f"Races after sync: {races_after}")
        
    except Exception as e:
        print(f"Error during sync: {e}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(debug_remington())