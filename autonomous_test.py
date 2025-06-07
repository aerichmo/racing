#!/usr/bin/env python3
"""
Autonomous testing system for race sync functionality.
This will continuously test and debug the sync process until it works.
"""

import asyncio
import httpx
import json
import time
from datetime import datetime, date
from typing import Dict, List, Any

class AutonomousRaceTester:
    def __init__(self):
        self.base_url = "https://racing-xqpi.onrender.com"
        self.test_results = []
        self.iteration = 0
        
    async def run_test_cycle(self) -> Dict[str, Any]:
        """Run a complete test cycle and return results"""
        self.iteration += 1
        print(f"\n{'='*60}")
        print(f"🔄 TEST CYCLE {self.iteration} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        results = {
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
            "tests": {}
        }
        
        # Test 1: Check API availability
        print("\n📡 Test 1: API Availability")
        api_test = await self.test_api_availability()
        results["tests"]["api_availability"] = api_test
        
        # Test 2: Check current races
        print("\n🏇 Test 2: Current Races Status")
        races_test = await self.test_current_races()
        results["tests"]["current_races"] = races_test
        
        # Test 3: Trigger race sync
        print("\n🔄 Test 3: Race Sync")
        sync_test = await self.test_race_sync()
        results["tests"]["race_sync"] = sync_test
        
        # Test 4: Check entries status
        print("\n🐴 Test 4: Race Entries Status")
        entries_test = await self.test_race_entries()
        results["tests"]["race_entries"] = entries_test
        
        # Test 5: Trigger entry sync
        print("\n🐴 Test 5: Entry Sync")
        entry_sync_test = await self.test_entry_sync()
        results["tests"]["entry_sync"] = entry_sync_test
        
        # Test 6: Check recommendations
        print("\n📊 Test 6: Recommendations")
        recommendations_test = await self.test_recommendations()
        results["tests"]["recommendations"] = recommendations_test
        
        # Test 7: Debug API internals
        print("\n🔍 Test 7: API Debug Info")
        debug_test = await self.test_debug_info()
        results["tests"]["debug_info"] = debug_test
        
        # Analyze results
        print("\n📋 CYCLE SUMMARY:")
        self.analyze_results(results)
        
        self.test_results.append(results)
        return results
    
    async def test_api_availability(self) -> Dict[str, Any]:
        """Test if API is responding"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/test")
                
                result = {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else None
                }
                
                if result["success"]:
                    print("   ✅ API is responding")
                else:
                    print(f"   ❌ API returned status {response.status_code}")
                
                return result
                
        except Exception as e:
            print(f"   ❌ API error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_current_races(self) -> Dict[str, Any]:
        """Check current race status in database"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/debug/races")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result = {
                        "success": True,
                        "total_races": data.get("total_races_in_db", 0),
                        "races_today": data.get("races_today", 0),
                        "today": data.get("today"),
                        "today_races_detail": data.get("today_races_detail", [])
                    }
                    
                    print(f"   📊 Total races in DB: {result['total_races']}")
                    print(f"   📅 Races today ({result['today']}): {result['races_today']}")
                    
                    if result['races_today'] > 0:
                        # Check Fair Meadows races
                        fm_races = [r for r in result['today_races_detail'] if r.get('track_id') == 2]
                        print(f"   🏇 Fair Meadows races: {len(fm_races)}")
                    
                    return result
                else:
                    print(f"   ❌ Failed to get race data: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
        except Exception as e:
            print(f"   ❌ Error checking races: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_race_sync(self) -> Dict[str, Any]:
        """Trigger race sync and analyze response"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                print("   🔄 Triggering race sync...")
                response = await client.post(f"{self.base_url}/api/sync")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result = {
                        "success": True,
                        "status": data.get("status"),
                        "races_synced": data.get("races_synced", 0),
                        "date": data.get("date"),
                        "debug": data.get("debug", [])
                    }
                    
                    print(f"   📊 Status: {result['status']}")
                    print(f"   🏇 Races synced: {result['races_synced']}")
                    
                    # Analyze debug info for Fair Meadows
                    if result['debug']:
                        for line in result['debug']:
                            if 'Fair Meadows' in line:
                                print(f"   🔍 {line}")
                    
                    return result
                else:
                    print(f"   ❌ Sync failed: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
        except Exception as e:
            print(f"   ❌ Error during sync: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_race_entries(self) -> Dict[str, Any]:
        """Check if races have entries"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Check Fair Meadows races
                response = await client.get(f"{self.base_url}/api/races/2")
                
                if response.status_code == 200:
                    races = response.json()
                    
                    result = {
                        "success": True,
                        "race_count": len(races),
                        "races_with_entries": 0,
                        "total_horses": 0,
                        "race_details": []
                    }
                    
                    for race in races:
                        horses = race.get("horses", [])
                        if len(horses) > 1 or (len(horses) == 1 and horses[0] != "Horses will be loaded in next layer"):
                            result["races_with_entries"] += 1
                        
                        result["total_horses"] += len([h for h in horses if h != "Horses will be loaded in next layer"])
                        
                        result["race_details"].append({
                            "race_number": race.get("race_number"),
                            "horse_count": len(horses),
                            "has_real_entries": len(horses) > 1
                        })
                    
                    print(f"   📊 Total races: {result['race_count']}")
                    print(f"   🐴 Races with entries: {result['races_with_entries']}")
                    print(f"   🏇 Total horses: {result['total_horses']}")
                    
                    return result
                else:
                    print(f"   ❌ Failed to get race entries: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
        except Exception as e:
            print(f"   ❌ Error checking entries: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_entry_sync(self) -> Dict[str, Any]:
        """Trigger entry sync"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                print("   🐴 Triggering entry sync...")
                response = await client.post(f"{self.base_url}/api/sync-entries")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result = {
                        "success": True,
                        "status": data.get("status"),
                        "entries_count": data.get("entries_count", 0),
                        "message": data.get("message"),
                        "error": data.get("error"),
                        "traceback": data.get("traceback")
                    }
                    
                    print(f"   📊 Status: {result['status']}")
                    print(f"   🐴 Entries count: {result['entries_count']}")
                    
                    if result.get("error"):
                        print(f"   ❌ Error: {result['error']}")
                        if result.get("traceback"):
                            print("   📋 Traceback:")
                            for line in result["traceback"].split('\n')[-5:]:
                                if line.strip():
                                    print(f"      {line}")
                    
                    return result
                else:
                    print(f"   ❌ Entry sync failed: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
        except Exception as e:
            print(f"   ❌ Error during entry sync: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_recommendations(self) -> Dict[str, Any]:
        """Check if recommendations are being generated"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Check Fair Meadows recommendations
                response = await client.get(f"{self.base_url}/api/recommendations/2")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result = {
                        "success": True,
                        "track_name": data.get("track_name"),
                        "recommendation_count": len(data.get("recommendations", [])),
                        "races_with_recommendations": 0,
                        "total_bets": 0
                    }
                    
                    for race in data.get("recommendations", []):
                        race_recs = race.get("recommendations", [])
                        if len(race_recs) > 0:
                            result["races_with_recommendations"] += 1
                            result["total_bets"] += len(race_recs)
                    
                    print(f"   🏇 Track: {result['track_name']}")
                    print(f"   📊 Races with recommendations: {result['races_with_recommendations']}")
                    print(f"   💰 Total bets: {result['total_bets']}")
                    
                    return result
                else:
                    print(f"   ❌ Failed to get recommendations: {response.status_code}")
                    return {"success": False, "status_code": response.status_code}
                    
        except Exception as e:
            print(f"   ❌ Error checking recommendations: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def test_debug_info(self) -> Dict[str, Any]:
        """Get detailed debug information"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test Fair Meadows API directly
                print("   🔍 Testing Fair Meadows API response format...")
                
                # We'll make a test request to understand the API format
                # This would need actual API credentials in production
                
                result = {
                    "success": True,
                    "notes": []
                }
                
                # Check if entry sync endpoint exists
                try:
                    response = await client.options(f"{self.base_url}/api/sync-entries")
                    if response.status_code == 405:  # Method not allowed means endpoint exists
                        result["notes"].append("Entry sync endpoint exists")
                    else:
                        result["notes"].append(f"Entry sync endpoint returned: {response.status_code}")
                except:
                    result["notes"].append("Could not verify entry sync endpoint")
                
                return result
                
        except Exception as e:
            print(f"   ❌ Debug error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def analyze_results(self, results: Dict[str, Any]):
        """Analyze test results and provide recommendations"""
        tests = results["tests"]
        
        # Determine current state
        api_working = tests.get("api_availability", {}).get("success", False)
        races_exist = tests.get("current_races", {}).get("races_today", 0) > 0
        entries_exist = tests.get("race_entries", {}).get("races_with_entries", 0) > 0
        recommendations_exist = tests.get("recommendations", {}).get("total_bets", 0) > 0
        
        print(f"\n   🎯 CURRENT STATE:")
        print(f"      API Working: {'✅' if api_working else '❌'}")
        print(f"      Races Exist: {'✅' if races_exist else '❌'} ({tests.get('current_races', {}).get('races_today', 0)} races)")
        print(f"      Entries Exist: {'✅' if entries_exist else '❌'} ({tests.get('race_entries', {}).get('races_with_entries', 0)} races with entries)")
        print(f"      Recommendations: {'✅' if recommendations_exist else '❌'} ({tests.get('recommendations', {}).get('total_bets', 0)} total)")
        
        # Diagnose issues
        print(f"\n   🔬 DIAGNOSIS:")
        
        if not api_working:
            print("      ❌ API is not responding - deployment may be in progress")
        elif not races_exist:
            print("      ❌ No races found for today - need to sync races")
        elif not entries_exist:
            print("      ❌ Races exist but no entries - need to sync entries")
            
            # Check entry sync error
            entry_sync = tests.get("entry_sync", {})
            if entry_sync.get("error"):
                print(f"      ❌ Entry sync error: {entry_sync.get('error')}")
                if "get_race_entries" in str(entry_sync.get("traceback", "")):
                    print("      🔧 Issue with API race entry format")
        elif not recommendations_exist:
            print("      ❌ Entries exist but no recommendations - betting engine issue")
        else:
            print("      ✅ System appears to be working correctly!")
        
        return {
            "api_working": api_working,
            "races_exist": races_exist,
            "entries_exist": entries_exist,
            "recommendations_exist": recommendations_exist
        }
    
    async def run_until_working(self, max_iterations: int = 10, delay: int = 30):
        """Run test cycles until the system is working or max iterations reached"""
        print(f"🚀 Starting autonomous testing (max {max_iterations} iterations)")
        print(f"⏱️  Will test every {delay} seconds")
        
        for i in range(max_iterations):
            results = await self.run_test_cycle()
            
            # Check if everything is working
            analysis = self.analyze_results(results)
            if all([
                analysis["api_working"],
                analysis["races_exist"],
                analysis["entries_exist"],
                analysis["recommendations_exist"]
            ]):
                print("\n🎉 SUCCESS! System is fully operational!")
                break
            
            if i < max_iterations - 1:
                print(f"\n⏳ Waiting {delay} seconds before next test...")
                await asyncio.sleep(delay)
        
        # Final report
        print("\n" + "="*60)
        print("📊 FINAL REPORT")
        print("="*60)
        
        if self.test_results:
            last_result = self.test_results[-1]
            analysis = self.analyze_results(last_result)
            
            print(f"\nTotal test cycles: {len(self.test_results)}")
            print(f"Final status:")
            print(f"  - API: {'✅ Working' if analysis['api_working'] else '❌ Not working'}")
            print(f"  - Races: {'✅ Synced' if analysis['races_exist'] else '❌ Not synced'}")
            print(f"  - Entries: {'✅ Synced' if analysis['entries_exist'] else '❌ Not synced'}")
            print(f"  - Recommendations: {'✅ Generated' if analysis['recommendations_exist'] else '❌ Not generated'}")
            
            # Save detailed results
            with open('test_results.json', 'w') as f:
                json.dump(self.test_results, f, indent=2)
            print(f"\n💾 Detailed results saved to test_results.json")

async def main():
    tester = AutonomousRaceTester()
    await tester.run_until_working(max_iterations=20, delay=30)

if __name__ == "__main__":
    asyncio.run(main())