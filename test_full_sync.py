#!/usr/bin/env python3
import asyncio
import os
import sys
from datetime import date

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql://mob1e_user:dU3nupu3FgdqClieo5JZWoZ2eL1KSMZB@dpg-d0lk5oogjchc73f5ieqg-a.oregon-postgres.render.com/mob1e'
os.environ['RACING_API_USERNAME'] = 'rUHkYRvkqy9sQhDpKC6nX2QI'
os.environ['RACING_API_PASSWORD'] = 'm3ByXQkl97YuKZqxlT56Tjn4'
os.environ['RACING_API_BASE_URL'] = 'https://api.theracingapi.com'

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import get_db, Base, get_engine, Track, Race, Bet, RaceEntry, Horse
from scheduler import RaceScheduler
from data_sync import DataSync

async def test_full_sync():
    # Initialize database
    Base.metadata.create_all(bind=get_engine())
    
    db = next(get_db())
    
    # Add tracks
    print("Adding tracks...")
    tracks = [
        {"name": "Remington Park", "code": "RP"},
        {"name": "Fair Meadows", "code": "FM"}
    ]
    for track_data in tracks:
        existing = db.query(Track).filter(Track.code == track_data["code"]).first()
        if not existing:
            track = Track(**track_data)
            db.add(track)
    db.commit()
    
    # Run initial sync
    print("\nRunning initial sync...")
    data_sync = DataSync()
    await data_sync.sync_initial_data(db)
    
    # Check results
    print("\n=== Sync Results ===")
    
    # Check tracks
    tracks = db.query(Track).all()
    print(f"\nTracks in database: {len(tracks)}")
    for track in tracks:
        print(f"  - {track.name} ({track.code})")
        
        # Check races for each track
        races = db.query(Race).filter(
            Race.track_id == track.id,
            Race.race_date == date.today()
        ).all()
        
        print(f"    Races: {len(races)}")
        
        for race in races[:3]:  # Show first 3 races
            print(f"      Race {race.race_number}: {race.race_time.strftime('%I:%M %p')}, {race.distance}f, {race.surface}")
    
    # Run pre-race sync to get entries
    print("\n\nRunning pre-race sync...")
    await data_sync.sync_pre_race_data(db)
    
    # Check entries
    print("\n=== Entry Results ===")
    rp = db.query(Track).filter(Track.code == "RP").first()
    if rp:
        first_race = db.query(Race).filter(
            Race.track_id == rp.id,
            Race.race_date == date.today()
        ).order_by(Race.race_number).first()
        
        if first_race:
            entries = db.query(RaceEntry).filter(RaceEntry.race_id == first_race.id).all()
            print(f"\nRemington Park Race 1 entries: {len(entries)}")
            for entry in entries[:5]:  # Show first 5
                horse = entry.horse
                print(f"  Post {entry.post_position}: {horse.name} - {entry.current_odds}:1")
    
    # Generate recommendations
    print("\n\nGenerating recommendations...")
    scheduler = RaceScheduler()
    await scheduler.generate_daily_recommendations(db)
    
    # Check bets
    print("\n=== Betting Results ===")
    if rp and first_race:
        bets = db.query(Bet).filter(Bet.race_id == first_race.id).all()
        print(f"\nRemington Park Race 1 bets: {len(bets)}")
        for bet in bets:
            entry = bet.entry
            if entry and entry.horse:
                print(f"  ${bet.amount} on {entry.horse.name} at {bet.odds}:1 (confidence: {bet.confidence*100:.1f}%)")
    
    db.close()
    print("\n✓ Full sync test completed!")

if __name__ == "__main__":
    asyncio.run(test_full_sync())