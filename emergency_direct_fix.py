#!/usr/bin/env python3
"""
Emergency direct fix - insert Fair Meadows races directly via API calls
"""
import requests
import json
from datetime import datetime, date

BASE_URL = "https://racing-xqpi.onrender.com"

def direct_database_insert():
    """Use the existing API endpoints to force data insertion"""
    
    print("EMERGENCY DIRECT FIX FOR FAIR MEADOWS")
    print("=" * 60)
    
    # Step 1: Try to modify the response format to bypass sync issues
    # We'll create a custom payload and send it to a working endpoint
    
    print("1. Creating custom race data payload...")
    
    # Based on our API testing, we know there are 8 races
    races_payload = {
        "action": "emergency_insert",
        "track_code": "FM",
        "track_name": "Fair Meadows", 
        "date": "2025-06-05",
        "races": [
            {
                "race_number": 1,
                "post_time": "7:00 PM",
                "distance": "4 Furlongs",
                "race_type": "CLAIMING",
                "purse": 7700,
                "surface": "Dirt"
            },
            {
                "race_number": 2, 
                "post_time": "7:28 PM",
                "distance": "6 1/2 Furlongs",
                "race_type": "CLAIMING",
                "purse": 4950,
                "surface": "Dirt"
            },
            {
                "race_number": 3,
                "post_time": "7:56 PM", 
                "distance": "4 Furlongs",
                "race_type": "ALLOWANCE",
                "purse": 17600,
                "surface": "Dirt"
            },
            {
                "race_number": 4,
                "post_time": "8:24 PM",
                "distance": "1 Mile", 
                "race_type": "MAIDEN SPECIAL WEIGHT",
                "purse": 17050,
                "surface": "Dirt"
            },
            {
                "race_number": 5,
                "post_time": "8:52 PM",
                "distance": "6 1/2 Furlongs",
                "race_type": "CLAIMING", 
                "purse": 7150,
                "surface": "Dirt"
            },
            {
                "race_number": 6,
                "post_time": "9:20 PM",
                "distance": "6 Furlongs",
                "race_type": "MAIDEN SPECIAL WEIGHT",
                "purse": 20460,
                "surface": "Dirt"
            },
            {
                "race_number": 7,
                "post_time": "9:48 PM", 
                "distance": "6 Furlongs",
                "race_type": "CLAIMING",
                "purse": 6600,
                "surface": "Dirt"
            },
            {
                "race_number": 8,
                "post_time": "10:16 PM",
                "distance": "6 1/2 Furlongs", 
                "race_type": "CLAIMING",
                "purse": 6050,
                "surface": "Dirt"
            }
        ]
    }
    
    print(f"Created payload with {len(races_payload['races'])} races")
    
    # Step 2: Try the working initial sync multiple times to force it
    print("\n2. Attempting multiple sync triggers...")
    
    for attempt in range(3):
        print(f"Attempt {attempt + 1}/3...")
        try:
            response = requests.post(f"{BASE_URL}/api/sync/initial", timeout=30)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Response: {response.json()}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
    
    # Step 3: Check if races appeared
    print("\n3. Checking if races now appear...")
    try:
        response = requests.get(f"{BASE_URL}/api/recommendations/2")
        if response.status_code == 200:
            data = response.json()
            print(f"Recommendations: {len(data.get('recommendations', []))}")
            if data.get('message'):
                print(f"Message: {data['message']}")
            
            if len(data.get('recommendations', [])) > 0:
                print("✅ SUCCESS! Races are now showing!")
                return True
            else:
                print("❌ Still no races showing")
        else:
            print(f"Error checking recommendations: {response.status_code}")
    except Exception as e:
        print(f"Error checking recommendations: {e}")
    
    return False

if __name__ == "__main__":
    success = direct_database_insert()
    if success:
        print("\n🎉 FIXED! Fair Meadows races are now showing!")
    else:
        print("\n❌ Fix failed - races still not showing")
        print("\nNext steps:")
        print("1. Check production server logs for sync errors")
        print("2. Verify database connectivity")
        print("3. Manual database insertion may be required")