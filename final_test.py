#!/usr/bin/env python3
"""Final autonomous test to verify complete Fair Meadows functionality"""

import asyncio
import httpx
import time

async def final_test():
    base_url = "https://racing-xqpi.onrender.com"
    
    print("🎯 FINAL AUTONOMOUS TEST - Fair Meadows Complete Functionality")
    print("="*70)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Wait for deployment
        print("\n⏳ Waiting for deployment (60 seconds)...")
        await asyncio.sleep(60)
        
        # Test 1: Check races exist
        print("\n1️⃣ Checking Fair Meadows races...")
        response = await client.get(f"{base_url}/api/races/2")
        if response.status_code == 200:
            races = response.json()
            print(f"   ✅ Found {len(races)} races")
        else:
            print(f"   ❌ Could not get races: {response.status_code}")
            return
        
        # Test 2: Trigger entry sync
        print("\n2️⃣ Triggering entry sync...")
        response = await client.post(f"{base_url}/api/sync-entries")
        if response.status_code == 200:
            data = response.json()
            print(f"   📊 Status: {data['status']}")
            print(f"   🐴 Entries synced: {data.get('entries_count', 0)}")
            
            if data.get('error'):
                print(f"   ❌ Error: {data['error']}")
                return
        else:
            print(f"   ❌ Entry sync failed: {response.status_code}")
            return
        
        # Test 3: Wait and check if entries populated
        print("\n3️⃣ Waiting for sync to complete (10 seconds)...")
        await asyncio.sleep(10)
        
        # Test 4: Check races now have entries
        print("\n4️⃣ Checking if races now have horses...")
        response = await client.get(f"{base_url}/api/races/2")
        if response.status_code == 200:
            races = response.json()
            races_with_horses = 0
            total_horses = 0
            
            for race in races:
                horses = race.get("horses", [])
                real_horses = [h for h in horses if h != "Horses will be loaded in next layer"]
                if real_horses:
                    races_with_horses += 1
                    total_horses += len(real_horses)
            
            print(f"   🏇 Races with horses: {races_with_horses}/{len(races)}")
            print(f"   🐴 Total horses: {total_horses}")
            
            if races_with_horses == 0:
                print("   ⚠️  Still no horses in races - checking database...")
                
                # Check database directly
                response = await client.get(f"{base_url}/api/debug/races")
                if response.status_code == 200:
                    debug_data = response.json()
                    print(f"      DB races today: {debug_data.get('races_today', 0)}")
        
        # Test 5: Check recommendations
        print("\n5️⃣ Checking recommendations...")
        response = await client.get(f"{base_url}/api/recommendations/2")
        if response.status_code == 200:
            data = response.json()
            races_with_recommendations = 0
            total_bets = 0
            
            for race in data.get("recommendations", []):
                recommendations = race.get("recommendations", [])
                if recommendations:
                    races_with_recommendations += 1
                    total_bets += len(recommendations)
            
            print(f"   💰 Races with recommendations: {races_with_recommendations}")
            print(f"   🎯 Total betting recommendations: {total_bets}")
        
        # Test 6: Final browser test
        print("\n6️⃣ Final browser verification...")
        try:
            # Simple GET to load the page
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                print("   ✅ Website accessible")
            else:
                print(f"   ❌ Website error: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Website error: {e}")
        
        # Final verdict
        print("\n" + "="*70)
        print("🏁 FINAL VERDICT")
        print("="*70)
        
        # Determine success
        success = False
        if races_with_horses > 0 and total_horses > 0:
            success = True
            print("🎉 SUCCESS! Fair Meadows races are populated with horses!")
            print(f"   ✅ {races_with_horses} races have horses")
            print(f"   ✅ {total_horses} total horses in races")
            
            if races_with_recommendations > 0:
                print(f"   ✅ {races_with_recommendations} races have betting recommendations")
                print("   🏆 COMPLETE SUCCESS - System fully operational!")
            else:
                print("   ⚠️  Horses synced but betting recommendations not yet generated")
                print("   📝 Next: Wait for betting engine to analyze entries")
        else:
            print("❌ ISSUE: Races still don't have horses populated")
            print("   🔧 The entry sync may need more debugging")
        
        return success

if __name__ == "__main__":
    success = asyncio.run(final_test())
    if success:
        print("\n🎯 Ready for user testing!")
    else:
        print("\n🔧 Additional debugging needed")