#!/usr/bin/env python3
import asyncio
import sys
import os
from datetime import date

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from racing_api import RacingAPIClient
from data_sync import DataSync
from database import get_db, Track, Race

async def debug_database():
    """Debug database sync issue"""
    print("DEBUGGING DATABASE SYNC")
    print("=" * 60)
    
    # 1. Test API directly
    client = RacingAPIClient()
    today = date.today()
    
    print(f"1. Testing API for Fair Meadows today ({today}):")
    try:
        races_data = await client.get_races_by_date('FM', today)
        races = races_data.get('races', [])
        print(f"API returns {len(races)} races for FM")
        
        if races:
            for race in races[:3]:
                print(f"  Race {race.get('race_number')}: {race.get('post_time')}")
        
        # Test entries
        if races:
            entries_data = await client.get_race_entries('FM', today, 1)
            entries = entries_data.get('entries', [])
            print(f"API returns {len(entries)} entries for Race 1")
            
    except Exception as e:
        print(f"API Error: {e}")
    
    # 2. Check database tracks
    print(f"\n2. Checking database tracks:")
    db = next(get_db())
    try:
        tracks = db.query(Track).all()
        for track in tracks:
            print(f"  Track {track.id}: '{track.name}' (code: {track.code})")
            
        # Check races for Fair Meadows track
        fm_track = db.query(Track).filter(Track.code == 'FM').first()
        if fm_track:
            races = db.query(Race).filter(
                Race.track_id == fm_track.id,
                Race.race_date == today
            ).all()
            print(f"\n  Fair Meadows track ID {fm_track.id} has {len(races)} races for today")
        else:
            print(f"\n  ❌ No track found with code 'FM'")
            
    finally:
        db.close()
    
    # 3. Test sync directly
    print(f"\n3. Testing sync manually:")
    try:
        db = next(get_db())
        sync = DataSync()
        
        print("Running sync for Fair Meadows...")
        track_name = "Fair Meadows Tulsa"  # Use API name
        track_code = "FM"
        
        # Ensure track exists
        track = db.query(Track).filter(Track.code == track_code).first()
        if not track:
            print(f"Creating track: {track_name}")
            track = Track(name=track_name, code=track_code)
            db.add(track)
            db.commit()
        else:
            print(f"Track exists: {track.name} (ID: {track.id})")
            
        # Try manual race sync
        races_data = await client.get_races_by_date(track_code, today)
        print(f"Got {len(races_data.get('races', []))} races from API")
        
        # Sync each race
        for race_info in races_data.get('races', []):
            print(f"Syncing race {race_info.get('race_number')}")
            await sync._sync_race(db, track.id, race_info, today)
            
        db.commit()
        
        # Check result
        races = db.query(Race).filter(
            Race.track_id == track.id,
            Race.race_date == today
        ).all()
        print(f"Database now has {len(races)} races for Fair Meadows today")
        
    except Exception as e:
        print(f"Sync Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_database())