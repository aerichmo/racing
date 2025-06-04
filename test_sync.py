#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from data_sync import DataSync
from database import Base, Track, Race
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Test different database URLs
DATABASE_URLS = [
    os.getenv("DATABASE_URL"),
    "postgresql://mob1e_user:dU3nupu3FgdqClieo5JZWoZ2eL1KSMZB@dpg-d0lk5oogjchc73f5ieqg-a.oregon-postgres.render.com/mob1e",
    "postgresql://mob1e_user:dU3nupu3FgdqClieo5JZWoZ2eL1KSMZB@dpg-d0lk5oogjchc73f5ieqg-a.oregon-postgres.render.com:5432/mob1e"
]

async def test_sync():
    for db_url in DATABASE_URLS:
        if not db_url:
            continue
            
        print(f"\nTrying database URL: {db_url[:50]}...")
        
        try:
            # Try to create engine
            engine = create_engine(db_url)
            
            # Test connection
            with engine.connect() as conn:
                result = conn.execute("SELECT 1")
                print("Database connection successful!")
                
            # Create session
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            
            # Check tracks
            tracks = db.query(Track).all()
            print(f"\nTracks in database: {[(t.name, t.code) for t in tracks]}")
            
            # Check if Fair Meadows exists
            fm_track = db.query(Track).filter(Track.code == "FM").first()
            if not fm_track:
                print("Creating Fair Meadows track...")
                fm_track = Track(name="Fair Meadows", code="FM")
                db.add(fm_track)
                db.commit()
                print("Fair Meadows track created!")
            
            # Check today's races
            today = datetime.now().date()
            fm_races = db.query(Race).filter(
                Race.track_id == fm_track.id,
                Race.race_date == today
            ).all()
            print(f"\nFair Meadows races today: {len(fm_races)}")
            
            # Try to sync data
            print("\nAttempting to sync Fair Meadows data...")
            sync = DataSync()
            
            # Test API directly first
            print("\nTesting API connection...")
            from racing_api import RacingAPIClient
            api = RacingAPIClient()
            
            # Debug API settings
            print(f"API Base URL: {api.base_url}")
            print(f"API Username: {api.username}")
            print(f"Auth header: {api.auth_header}")
            
            try:
                # Try a simple API call
                tracks_data = await api.get_tracks()
                print(f"API tracks response: {tracks_data}")
            except Exception as api_error:
                print(f"API error: {api_error}")
                
                # Try races endpoint
                try:
                    races_data = await api.get_races_by_date("FM", today)
                    print(f"Fair Meadows races from API: {races_data}")
                except Exception as races_error:
                    print(f"Races API error: {races_error}")
            
            # Try sync
            await sync.sync_initial_data(db)
            
            # Check races again
            fm_races_after = db.query(Race).filter(
                Race.track_id == fm_track.id,
                Race.race_date == today
            ).all()
            print(f"\nFair Meadows races after sync: {len(fm_races_after)}")
            
            db.close()
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            
    return False

if __name__ == "__main__":
    success = asyncio.run(test_sync())
    if success:
        print("\nSync test completed successfully!")
    else:
        print("\nSync test failed!")