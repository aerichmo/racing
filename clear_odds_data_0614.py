#!/usr/bin/env python3
"""
Script to clear live odd data for 6/14
This will:
1. Clear current_odds from RaceEntry table for races on 6/14
2. Delete OddsHistory records for races on 6/14
"""

import sys
import os
from datetime import date
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'horse-racing-platform', 'src'))

from database import Race, RaceEntry, OddsHistory, get_session_local

def clear_odds_for_date(target_date):
    # Get database session using the database module's session
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        # Find all races for the target date
        races = db.query(Race).filter(
            Race.race_date == target_date
        ).all()
        
        if not races:
            print(f"No races found for {target_date}")
            return
        
        print(f"Found {len(races)} races for {target_date}")
        
        # Counter for affected records
        entries_cleared = 0
        history_deleted = 0
        
        for race in races:
            print(f"\nProcessing Race ID: {race.id}, Track: {race.track_id}, Race Number: {race.race_number}")
            
            # Clear current_odds from race entries
            entries = db.query(RaceEntry).filter(
                RaceEntry.race_id == race.id,
                RaceEntry.current_odds.isnot(None)
            ).all()
            
            for entry in entries:
                print(f"  Clearing odds for entry {entry.id}: {entry.horse_name} (was {entry.current_odds})")
                entry.current_odds = None
                entries_cleared += 1
            
            # Delete odds history for this race's entries
            entry_ids = [e.id for e in db.query(RaceEntry).filter(RaceEntry.race_id == race.id).all()]
            if entry_ids:
                history_count = db.query(OddsHistory).filter(
                    OddsHistory.entry_id.in_(entry_ids)
                ).count()
                
                if history_count > 0:
                    db.query(OddsHistory).filter(
                        OddsHistory.entry_id.in_(entry_ids)
                    ).delete(synchronize_session=False)
                    history_deleted += history_count
                    print(f"  Deleted {history_count} odds history records")
        
        # Commit the changes
        db.commit()
        print(f"\n✓ Successfully cleared odds data for {target_date}")
        print(f"  - Cleared current odds from {entries_cleared} entries")
        print(f"  - Deleted {history_deleted} odds history records")
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ Error clearing odds data: {str(e)}")
        raise
    finally:
        db.close()

def main():
    # Target date: June 14, 2024 (adjust year as needed)
    target_date = date(2024, 6, 14)
    
    print(f"This script will clear all live odd data for {target_date}")
    print("This includes:")
    print("  - Setting current_odds to NULL in race_entries table")
    print("  - Deleting all records from odds_history table")
    print("\nThis action cannot be undone!")
    
    response = input("\nDo you want to proceed? (yes/no): ")
    if response.lower() == 'yes':
        clear_odds_for_date(target_date)
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    main()