#!/usr/bin/env python3
"""
Automated debugging and fixing mechanism for racing recommendations
"""

import asyncio
import httpx
import json
from datetime import date, datetime
import os
from typing import Dict, List

# Base URL for the deployed application
BASE_URL = "https://racing-xqpi.onrender.com"

class RacingDebugger:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = httpx.AsyncClient()
        
    async def run_full_diagnostic(self):
        """Run complete diagnostic and attempt to fix issues"""
        print("🔍 Starting Racing Platform Diagnostic...")
        print("=" * 60)
        
        # Step 1: Basic connectivity test
        await self._test_basic_connectivity()
        
        # Step 2: Check tracks
        tracks = await self._check_tracks()
        
        # Step 3: Check races in database
        races_info = await self._check_races_in_db()
        
        # Step 4: Test API data sync
        await self._test_api_sync()
        
        # Step 5: Check race entries sync
        await self._check_race_entries()
        
        # Step 6: Test recommendations after sync
        await self._test_recommendations_post_sync(tracks)
        
        # Step 7: Manual betting data generation if needed
        await self._generate_betting_data_if_needed()
        
        # Final test
        await self._final_recommendations_test(tracks)
        
        print("\n" + "=" * 60)
        print("🎯 Diagnostic Complete!")
        
    async def _test_basic_connectivity(self):
        """Test basic API connectivity"""
        print("\n1️⃣ Testing Basic Connectivity")
        print("-" * 30)
        
        try:
            response = await self.session.get(f"{self.base_url}/api/test")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API is responding: {data['message']}")
                print(f"📅 Server time: {data['timestamp']}")
            else:
                print(f"❌ API responded with status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            
    async def _check_tracks(self):
        """Check available tracks"""
        print("\n2️⃣ Checking Tracks")
        print("-" * 30)
        
        try:
            response = await self.session.get(f"{self.base_url}/api/tracks")
            tracks = response.json()
            
            print(f"✅ Found {len(tracks)} tracks:")
            for track in tracks:
                print(f"   • {track['name']} (ID: {track['id']})")
                
            return tracks
            
        except Exception as e:
            print(f"❌ Failed to get tracks: {e}")
            return []
            
    async def _check_races_in_db(self):
        """Check races currently in database"""
        print("\n3️⃣ Checking Races in Database")
        print("-" * 30)
        
        try:
            response = await self.session.get(f"{self.base_url}/api/debug/races")
            data = response.json()
            
            print(f"📊 Total races in DB: {data['total_races_in_db']}")
            print(f"📅 Races for today ({data['today']}): {data['races_today']}")
            
            if data['races_today'] > 0:
                print("🏁 Today's races:")
                for race in data['today_races_detail']:
                    print(f"   Race {race['race_number']}: {race['race_type']} - ${race['purse']:,}")
            else:
                print("⚠️ No races scheduled for today")
                
            return data
            
        except Exception as e:
            print(f"❌ Failed to check races: {e}")
            return {}
            
    async def _test_api_sync(self):
        """Test the API sync to get fresh race data"""
        print("\n4️⃣ Testing API Data Sync")
        print("-" * 30)
        
        try:
            print("🔄 Triggering race sync...")
            response = await self.session.post(f"{self.base_url}/api/sync")
            data = response.json()
            
            print(f"📡 Sync Status: {data['status']}")
            print(f"🏁 Races Synced: {data.get('races_synced', 0)}")
            
            if 'debug' in data:
                print("🔍 Debug Info:")
                for debug_line in data['debug'][-5:]:  # Show last 5 debug lines
                    print(f"   {debug_line}")
                    
            if data.get('races_synced', 0) == 0:
                print("⚠️ No new races synced - may be normal if no racing today")
                
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            
    async def _check_race_entries(self):
        """Check and sync race entries (horses, jockeys, trainers)"""
        print("\n5️⃣ Syncing Race Entries")
        print("-" * 30)
        
        try:
            print("🐎 Triggering entries sync...")
            response = await self.session.post(f"{self.base_url}/api/sync-entries")
            data = response.json()
            
            print(f"📡 Entry Sync Status: {data['status']}")
            print(f"🐎 Entries Count: {data.get('entries_count', 0)}")
            
            if data.get('entries_count', 0) == 0:
                print("⚠️ No entries found - this may be why recommendations are empty")
            else:
                print("✅ Race entries successfully synced")
                
        except Exception as e:
            print(f"❌ Entry sync failed: {e}")
            
    async def _test_recommendations_post_sync(self, tracks):
        """Test recommendations after syncing data"""
        print("\n6️⃣ Testing Recommendations After Sync")
        print("-" * 30)
        
        for track in tracks:
            try:
                print(f"🎯 Testing {track['name']}...")
                response = await self.session.get(f"{self.base_url}/api/recommendations/{track['id']}")
                data = response.json()
                
                if 'recommendations' in data:
                    total_recs = sum(len(race['recommendations']) for race in data['recommendations'])
                    print(f"   📊 {track['name']}: {len(data['recommendations'])} races, {total_recs} total recommendations")
                    
                    if total_recs == 0:
                        print(f"   ⚠️ {track['name']}: No betting recommendations generated")
                    else:
                        print(f"   ✅ {track['name']}: Recommendations working!")
                        
                elif 'message' in data:
                    print(f"   ℹ️ {track['name']}: {data['message']}")
                    
            except Exception as e:
                print(f"   ❌ {track['name']}: Failed to test recommendations - {e}")
                
    async def _generate_betting_data_if_needed(self):
        """Generate artificial betting data to test the system"""
        print("\n7️⃣ Generating Test Betting Data")
        print("-" * 30)
        
        try:
            # First check if we have any recommendations
            response = await self.session.get(f"{self.base_url}/api/recommendations/2")  # Fair Meadows
            data = response.json()
            
            total_recs = sum(len(race['recommendations']) for race in data.get('recommendations', []))
            
            if total_recs == 0:
                print("🔧 No recommendations found - generating test betting data...")
                
                # Create a simple endpoint to generate test bets
                test_data_payload = {
                    "action": "generate_test_bets",
                    "track_id": 2,  # Fair Meadows
                    "races_count": 3  # Generate for first 3 races
                }
                
                # Note: We'd need to create this endpoint, but for now we'll suggest the manual approach
                print("💡 Recommendation: Add test betting data generation endpoint")
                print("   This would create sample bets and historical performance data")
                print("   to demonstrate the betting recommendations system")
                
        except Exception as e:
            print(f"❌ Failed to generate test data: {e}")
            
    async def _final_recommendations_test(self, tracks):
        """Final test of recommendations system"""
        print("\n8️⃣ Final Recommendations Test")
        print("-" * 30)
        
        working_tracks = 0
        
        for track in tracks:
            try:
                response = await self.session.get(f"{self.base_url}/api/recommendations/{track['id']}")
                data = response.json()
                
                if 'recommendations' in data:
                    total_recs = sum(len(race['recommendations']) for race in data['recommendations'])
                    races_count = len(data['recommendations'])
                    
                    print(f"🏁 {track['name']}: {races_count} races, {total_recs} recommendations")
                    
                    if total_recs > 0:
                        working_tracks += 1
                        # Show sample recommendation
                        for race in data['recommendations']:
                            if race['recommendations']:
                                sample_rec = race['recommendations'][0]
                                print(f"   📊 Sample: Race {race['race_number']} - {sample_rec['horse_name']} "
                                      f"({sample_rec['confidence']:.1f}% confidence, ${sample_rec['bet_amount']} bet)")
                                break
                elif 'message' in data:
                    print(f"ℹ️ {track['name']}: {data['message']}")
                    
            except Exception as e:
                print(f"❌ {track['name']}: {e}")
                
        print(f"\n🎯 Summary: {working_tracks}/{len(tracks)} tracks have working recommendations")
        
        if working_tracks == 0:
            print("\n🔧 NEXT STEPS TO FIX:")
            print("1. The system has races but no race entries (horses)")
            print("2. Without horses, no betting recommendations can be generated")
            print("3. Need to sync race entries from Racing API")
            print("4. May need historical performance data for ML predictions")
            
    async def close(self):
        """Clean up resources"""
        await self.session.aclose()

async def main():
    """Run the diagnostic"""
    debugger = RacingDebugger()
    try:
        await debugger.run_full_diagnostic()
    finally:
        await debugger.close()

if __name__ == "__main__":
    asyncio.run(main())