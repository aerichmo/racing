#!/usr/bin/env python3
"""
Deep debugging script for Fair Meadows API to understand race data structure
and locate where horse entries are stored.
"""

import requests
import json
from datetime import datetime, timedelta
from pprint import pprint
import sys

# Configuration
BASE_URL = "https://api.fairmeadows.com/v1"
API_KEY = "fmapi_test_key_2024"  # Replace with actual API key

def make_api_call(endpoint, params=None):
    """Make API call with proper headers and error handling."""
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }
    
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Making API call to: {url}")
    if params:
        print(f"Parameters: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error response: {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

def analyze_race_structure(race_data):
    """Analyze the structure of a race object."""
    print("\n" + "="*60)
    print("ANALYZING RACE STRUCTURE")
    print("="*60)
    
    # Basic race info
    print(f"\nRace ID: {race_data.get('id', 'N/A')}")
    print(f"Race Number: {race_data.get('number', 'N/A')}")
    print(f"Race Name: {race_data.get('name', 'N/A')}")
    print(f"Post Time: {race_data.get('post_time', 'N/A')}")
    
    # List all top-level keys
    print(f"\nTop-level keys in race object:")
    for key in sorted(race_data.keys()):
        value_type = type(race_data[key]).__name__
        value_preview = str(race_data[key])[:50] + "..." if len(str(race_data[key])) > 50 else str(race_data[key])
        print(f"  - {key}: {value_type} = {value_preview}")
    
    # Look for potential entry fields
    print("\n" + "-"*40)
    print("SEARCHING FOR ENTRY/HORSE DATA")
    print("-"*40)
    
    potential_entry_fields = [
        'entries', 'horses', 'competitors', 'starters', 'runners',
        'participants', 'entrants', 'field', 'race_entries', 'race_horses'
    ]
    
    found_entries = False
    for field in potential_entry_fields:
        if field in race_data:
            found_entries = True
            print(f"\n✓ Found '{field}' field!")
            field_data = race_data[field]
            
            if isinstance(field_data, list):
                print(f"  - Type: list")
                print(f"  - Length: {len(field_data)}")
                
                if len(field_data) > 0:
                    print(f"  - First item structure:")
                    first_item = field_data[0]
                    if isinstance(first_item, dict):
                        for key, value in first_item.items():
                            print(f"    • {key}: {type(value).__name__} = {str(value)[:30]}...")
                    else:
                        print(f"    • {type(first_item).__name__}: {first_item}")
            
            elif isinstance(field_data, dict):
                print(f"  - Type: dict")
                print(f"  - Keys: {list(field_data.keys())}")
            
            else:
                print(f"  - Type: {type(field_data).__name__}")
                print(f"  - Value: {field_data}")
    
    if not found_entries:
        print("\n❌ No obvious entry fields found in standard locations")
        
        # Check for nested structures
        print("\nChecking for nested entry data...")
        for key, value in race_data.items():
            if isinstance(value, dict):
                print(f"\nChecking nested dict '{key}':")
                for nested_key in value.keys():
                    if any(term in nested_key.lower() for term in ['entry', 'horse', 'runner', 'starter']):
                        print(f"  ✓ Found potential: {nested_key}")
                        nested_value = value[nested_key]
                        if isinstance(nested_value, list):
                            print(f"    - List with {len(nested_value)} items")
                        else:
                            print(f"    - {type(nested_value).__name__}")

def test_different_endpoints():
    """Test different API endpoints to find entry data."""
    print("\n" + "="*60)
    print("TESTING DIFFERENT API ENDPOINTS")
    print("="*60)
    
    # Test 1: Get races for today
    today = datetime.now().strftime('%Y-%m-%d')
    races_data = make_api_call('/races', {'date': today})
    
    if races_data and 'races' in races_data:
        races = races_data['races']
        print(f"\nFound {len(races)} races for {today}")
        
        if len(races) > 0:
            # Analyze first race in detail
            first_race = races[0]
            analyze_race_structure(first_race)
            
            # Test 2: Try getting specific race details
            race_id = first_race.get('id')
            if race_id:
                print("\n" + "="*60)
                print("TESTING INDIVIDUAL RACE ENDPOINT")
                print("="*60)
                
                # Try different endpoint patterns
                endpoints_to_try = [
                    f'/races/{race_id}',
                    f'/races/{race_id}/entries',
                    f'/races/{race_id}/horses',
                    f'/races/{race_id}/starters',
                    f'/race/{race_id}',
                    f'/race/{race_id}/entries'
                ]
                
                for endpoint in endpoints_to_try:
                    result = make_api_call(endpoint)
                    if result:
                        print(f"\n✓ Success with {endpoint}")
                        print(f"Response keys: {list(result.keys())}")
                        
                        # Check for entry data
                        for key in result.keys():
                            if any(term in key.lower() for term in ['entry', 'horse', 'runner', 'starter']):
                                print(f"  → Found potential entry data in '{key}'")
                                if isinstance(result[key], list):
                                    print(f"    List with {len(result[key])} items")
    else:
        print("\n❌ No races found or error in API call")

def print_complete_race_json():
    """Print complete JSON structure of a race for manual inspection."""
    print("\n" + "="*60)
    print("COMPLETE RACE JSON STRUCTURE")
    print("="*60)
    
    today = datetime.now().strftime('%Y-%m-%d')
    races_data = make_api_call('/races', {'date': today})
    
    if races_data and 'races' in races_data and len(races_data['races']) > 0:
        first_race = races_data['races'][0]
        print("\nComplete structure of first race:")
        print(json.dumps(first_race, indent=2))
        
        # Save to file for easier inspection
        with open('fair_meadows_race_structure.json', 'w') as f:
            json.dump(first_race, f, indent=2)
        print("\n✓ Also saved to 'fair_meadows_race_structure.json' for detailed inspection")
    else:
        print("\n❌ Could not retrieve race data")

def main():
    """Main execution function."""
    print("FAIR MEADOWS API DEEP DEBUG")
    print("="*60)
    print(f"Started at: {datetime.now()}")
    
    # Run all tests
    test_different_endpoints()
    print_complete_race_json()
    
    print("\n" + "="*60)
    print("DEBUGGING COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Check the console output above for the location of entry data")
    print("2. Review 'fair_meadows_race_structure.json' for complete structure")
    print("3. Update the entry sync code to use the correct field path")

if __name__ == "__main__":
    # Check if API key is set
    if API_KEY == "fmapi_test_key_2024":
        print("⚠️  WARNING: Using default test API key. Replace with actual Fair Meadows API key.")
        print("Update the API_KEY variable at the top of this script.")
        response = input("\nContinue with test key? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    main()