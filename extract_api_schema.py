#!/usr/bin/env python3
import asyncio
import sys
import os
from datetime import date
import json
from pprint import pprint

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from racing_api import RacingAPIClient

async def extract_all_schemas():
    """Extract and document all API response schemas"""
    client = RacingAPIClient()
    
    print("API RESPONSE SCHEMAS")
    print("=" * 80)
    
    # 1. List Meets Schema
    print("\n1. LIST MEETS ENDPOINT")
    print("URL: https://api.theracingapi.com/v1/north-america/meets")
    print("-" * 60)
    
    try:
        meets = await client.get_meets('2025-06-11')  # Date with Fair Meadows
        print(f"Response Type: {type(meets)}")
        print(f"Number of meets: {len(meets)}")
        
        if meets:
            print(f"\nSample meet structure:")
            sample_meet = meets[0]
            print(f"Keys: {list(sample_meet.keys())}")
            print("Full sample meet:")
            print(json.dumps(sample_meet, indent=2))
            
            # Find Fair Meadows specifically
            fmt_meets = [m for m in meets if m.get('track_id') == 'FMT']
            if fmt_meets:
                print(f"\nFair Meadows Tulsa meet:")
                print(json.dumps(fmt_meets[0], indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
    
    # 2. Meet Entries Schema  
    print(f"\n\n2. MEET ENTRIES ENDPOINT")
    print("URL: https://api.theracingapi.com/v1/north-america/meets/{meet_id}/entries")
    print("-" * 60)
    
    try:
        # Use Fair Meadows meet ID
        meet_id = "FMT_1749614400000"
        entries_data = await client.get_meet_entries(meet_id)
        
        print(f"Response Type: {type(entries_data)}")
        print(f"Top-level keys: {list(entries_data.keys())}")
        
        if 'races' in entries_data:
            races = entries_data['races']
            print(f"Number of races: {len(races)}")
            
            if races:
                print(f"\nSample race structure:")
                sample_race = races[0]
                print(f"Race keys: {list(sample_race.keys())}")
                
                # Show race details
                print(f"\nRace details sample:")
                race_info = {k: v for k, v in sample_race.items() if k != 'runners'}
                print(json.dumps(race_info, indent=2))
                
                # Show runner structure
                if 'runners' in sample_race:
                    runners = sample_race['runners']
                    print(f"\nNumber of runners in race: {len(runners)}")
                    
                    if runners:
                        print(f"\nSample runner structure:")
                        sample_runner = runners[0]
                        print(f"Runner keys: {list(sample_runner.keys())}")
                        print("Full sample runner:")
                        print(json.dumps(sample_runner, indent=2))
                        
                        # Check jockey structure
                        if 'jockey' in sample_runner:
                            print(f"\nJockey structure:")
                            print(json.dumps(sample_runner['jockey'], indent=2))
                        
                        # Check trainer structure
                        if 'trainer' in sample_runner:
                            print(f"\nTrainer structure:")
                            print(json.dumps(sample_runner['trainer'], indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Meet Results Schema
    print(f"\n\n3. MEET RESULTS ENDPOINT")
    print("URL: https://api.theracingapi.com/v1/north-america/meets/{meet_id}/results")
    print("-" * 60)
    
    try:
        meet_id = "FMT_1749614400000"
        results_data = await client.get_meet_results(meet_id)
        
        print(f"Response Type: {type(results_data)}")
        
        if results_data:
            print(f"Number of results: {len(results_data)}")
            if results_data:
                print(f"Sample result structure:")
                print(json.dumps(results_data[0], indent=2))
        else:
            print("No results available (races not yet finished)")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # 4. All field mappings for reference
    print(f"\n\n4. FIELD MAPPINGS FOR OUR APPLICATION")
    print("-" * 60)
    
    print("""
    MEETS RESPONSE:
    - track_id: Track identifier (e.g., 'FMT' for Fair Meadows Tulsa)
    - track_name: Full track name (e.g., 'Fair Meadows Tulsa')
    - meet_id: Unique meet identifier (e.g., 'FMT_1749614400000')
    - date: Meet date (YYYY-MM-DD format)
    - country: Country code ('USA')
    
    ENTRIES RESPONSE:
    Race level:
    - race_key.race_number: Race number (string, convert to int)
    - post_time: Race post time (e.g., '7:00 PM')
    - distance_description: Distance (e.g., '4 Furlongs')
    - surface_description: Surface type (e.g., 'Dirt')
    - race_type_description: Race type (e.g., 'CLAIMING')
    - race_class: Race conditions/class
    - purse: Race purse amount
    
    Runner level:
    - horse_name: Horse name
    - registration_number: Unique horse ID
    - program_number: Post position (string, convert to int)
    - weight: Jockey weight (string, convert to int)
    - morning_line_odds: Morning line odds (string, convert to float)
    - medication: Medication codes (e.g., 'L')
    - equipment: Equipment codes (e.g., 'b', 'f')
    - jockey.id: Jockey unique ID
    - jockey.first_name_initial: Jockey first initial
    - jockey.last_name: Jockey last name
    - trainer.id: Trainer unique ID  
    - trainer.first_name: Trainer first name
    - trainer.last_name: Trainer last name
    
    RESULTS RESPONSE:
    TBD - Need to see actual race results when available
    """)

if __name__ == "__main__":
    asyncio.run(extract_all_schemas())