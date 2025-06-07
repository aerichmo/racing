import httpx
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import base64
from dotenv import load_dotenv

load_dotenv()

class RacingAPIClient:
    def __init__(self):
        self.base_url = os.getenv("RACING_API_BASE_URL", "https://api.theracingapi.com")
        self.username = os.getenv("RACING_API_USERNAME")
        self.password = os.getenv("RACING_API_PASSWORD")
        self.auth_header = self._create_auth_header()
        
    def _create_auth_header(self):
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    
    async def get_tracks(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/tracks",
                headers=self.auth_header
            )
            response.raise_for_status()
            return response.json()
    
    async def get_races_by_date(self, track_code: str, race_date: date):
        # Map internal track codes to API track codes with fallbacks
        track_map = {
            'FM': ['FMT', 'FP'],  # Fair Meadows -> try Fair Meadows Tulsa, then Fairmount Park
            'RP': ['RP']    # Remington Park stays the same
        }
        
        possible_codes = track_map.get(track_code, [track_code])
        if isinstance(possible_codes, str):
            possible_codes = [possible_codes]
        
        async with httpx.AsyncClient() as client:
            # First, get list of meets to find the meet_id for this track/date
            target_date = race_date.strftime('%Y-%m-%d')
            meets_response = await client.get(
                f"{self.base_url}/v1/north-america/meets",
                headers=self.auth_header,
                params={
                    'start_date': target_date,
                    'end_date': target_date
                }
            )
            meets_response.raise_for_status()
            meets_data = meets_response.json()
            
            # Debug: log all meets to help troubleshoot
            all_track_ids = [meet.get('track_id', '') for meet in meets_data.get('meets', [])]
            all_tracks_info = [(meet.get('track_id', ''), meet.get('track_name', '')) for meet in meets_data.get('meets', [])]
            
            # Try each possible track code
            meet_id = None
            used_track_code = None
            
            for api_track_code in possible_codes:
                for meet in meets_data.get('meets', []):
                    if meet.get('track_id') == api_track_code and meet.get('date') == target_date:
                        meet_id = meet.get('meet_id')
                        used_track_code = api_track_code
                        break
                if meet_id:
                    break
            
            if not meet_id:
                # Return debug info when no meet found
                return {
                    "entries": [],
                    "debug": {
                        "looking_for": possible_codes,
                        "found_tracks": all_track_ids,
                        "found_tracks_detail": all_tracks_info,
                        "date": target_date
                    }
                }
            
            # Now get the entries for this meet (which contains race info)
            entries_response = await client.get(
                f"{self.base_url}/v1/north-america/meets/{meet_id}/entries",
                headers=self.auth_header
            )
            entries_response.raise_for_status()
            result = entries_response.json()
            
            # Add debug info about which track code worked
            if 'debug' not in result:
                result['debug'] = {}
            result['debug']['used_track_code'] = used_track_code
            result['debug']['tried_codes'] = possible_codes
            
            return result
    
    async def get_race_entries(self, track_code: str, race_date: date, race_number: int):
        # This method now gets entries for a specific race from the meet entries
        # We'll get all meet entries and filter for the specific race
        race_data = await self.get_races_by_date(track_code, race_date)
        
        # Handle both 'entries' and 'races' formats
        if 'races' in race_data and 'entries' not in race_data:
            # For 'races' format, find the specific race and get its entries
            debug_info = []
            for i, race in enumerate(race_data.get('races', [])):
                # Extract race number from race_key if needed
                race_key = race.get('race_key', {})
                if isinstance(race_key, dict):
                    race_num = race_key.get('race_number')
                else:
                    race_num = race.get('race_number')
                
                debug_info.append(f"Race {i+1}: race_num={race_num} (type: {type(race_num)}), looking_for={race_number} (type: {type(race_number)})")
                
                # Ensure both are the same type for comparison
                if race_num is not None and int(race_num) == int(race_number):
                    # Fair Meadows uses 'runners' instead of 'entries'
                    entries = race.get('entries', []) or race.get('runners', [])
                    debug_info.append(f"MATCH! Found {len(entries)} entries/runners")
                    return {"entries": entries, "debug": debug_info}
            
            return {"entries": [], "debug": debug_info}  # No matching race found
        else:
            # For 'entries' format, filter by race number
            race_entries = []
            for entry in race_data.get('entries', []):
                if entry.get('race_number') == race_number:
                    race_entries.append(entry)
            
            return {"entries": race_entries}
    
    async def get_race_results(self, track_code: str, race_date: date, race_number: int):
        # Map internal track codes to API track codes with fallbacks
        track_map = {
            'FM': ['FMT', 'FP'],  # Fair Meadows -> try Fair Meadows Tulsa, then Fairmount Park
            'RP': ['RP']    # Remington Park stays the same
        }
        
        possible_codes = track_map.get(track_code, [track_code])
        if isinstance(possible_codes, str):
            possible_codes = [possible_codes]
        
        async with httpx.AsyncClient() as client:
            try:
                # First, get list of meets to find the meet_id for this track/date
                target_date = race_date.strftime('%Y-%m-%d')
                meets_response = await client.get(
                    f"{self.base_url}/v1/north-america/meets",
                    headers=self.auth_header,
                    params={
                        'start_date': target_date,
                        'end_date': target_date
                    }
                )
                meets_response.raise_for_status()
                meets_data = meets_response.json()
                
                # Try each possible track code
                meet_id = None
                
                for api_track_code in possible_codes:
                    for meet in meets_data.get('meets', []):
                        if meet.get('track_id') == api_track_code and meet.get('date') == target_date:
                            meet_id = meet.get('meet_id')
                            break
                    if meet_id:
                        break
                
                if not meet_id:
                    return None  # No meet found for this track/date
                
                # Get results for this meet
                results_response = await client.get(
                    f"{self.base_url}/v1/north-america/meets/{meet_id}/results",
                    headers=self.auth_header
                )
                results_response.raise_for_status()
                results_data = results_response.json()
                
                # Filter results for the specific race number
                race_results = []
                for result in results_data.get('results', []):
                    if result.get('race_number') == race_number:
                        race_results.append(result)
                
                return {"results": race_results}
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
    
    async def get_horse_history(self, registration_number: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/horses/{registration_number}/history",
                headers=self.auth_header
            )
            response.raise_for_status()
            return response.json()
    
    async def get_jockey_stats(self, jockey_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/jockeys/{jockey_id}/stats",
                headers=self.auth_header
            )
            response.raise_for_status()
            return response.json()
    
    async def get_trainer_stats(self, trainer_id: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/trainers/{trainer_id}/stats",
                headers=self.auth_header
            )
            response.raise_for_status()
            return response.json()
    
    async def get_track_conditions(self, track_code: str, race_date: date):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/conditions/{track_code}/{race_date.strftime('%Y-%m-%d')}",
                headers=self.auth_header
            )
            response.raise_for_status()
            return response.json()