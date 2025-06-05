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
    
    async def get_meets(self, date_str: Optional[str] = None):
        """Get meets for a specific date or all upcoming meets"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/v1/north-america/meets"
            params = {"date": date_str} if date_str else {}
            
            response = await client.get(url, headers=self.auth_header, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('meets', [])
    
    async def get_meet_entries(self, meet_id: str):
        """Get all entries for a specific meet"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/v1/north-america/meets/{meet_id}/entries"
            response = await client.get(url, headers=self.auth_header)
            response.raise_for_status()
            return response.json()
    
    async def get_meet_results(self, meet_id: str):
        """Get all results for a specific meet"""
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/v1/north-america/meets/{meet_id}/results"
            try:
                response = await client.get(url, headers=self.auth_header)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return []  # No results yet
                raise
    
    # Legacy methods for backward compatibility - will be refactored
    async def get_races_by_date(self, track_code: str, race_date: date):
        """Get races for a track on a specific date"""
        # Convert to new API format
        date_str = race_date.strftime('%Y-%m-%d')
        meets = await self.get_meets(date_str)
        
        # Find meets for the requested track
        # Note: Fair Meadows is FMT, not FM
        track_map = {
            'FM': 'FMT',  # Fair Meadows -> Fair Meadows Tulsa
            'RP': 'RP'    # Remington Park stays the same
        }
        
        actual_track_code = track_map.get(track_code, track_code)
        track_meets = [m for m in meets if m.get('track_id') == actual_track_code]
        
        if not track_meets:
            return {'races': []}
        
        # Get entries for the meet to build race info
        meet = track_meets[0]
        entries_data = await self.get_meet_entries(meet['meet_id'])
        
        # Extract races from the response structure
        races_list = []
        if 'races' in entries_data:
            for race in entries_data['races']:
                race_key = race.get('race_key', {})
                race_number = int(race_key.get('race_number', 1))
                
                races_list.append({
                    'id': f"{meet['meet_id']}_R{race_number}",
                    'race_number': race_number,
                    'post_time': f"{race_date}T{race.get('post_time', '13:00')}",
                    'distance': race.get('distance_description', '6 furlongs'),
                    'surface': race.get('surface_description', 'Dirt'),
                    'race_type': race.get('race_type_description', 'Claiming'),
                    'purse': race.get('purse', 25000),
                    'conditions': race.get('race_class', '')
                })
        
        return {'races': sorted(races_list, key=lambda x: x['race_number'])}
    
    async def get_race_entries(self, track_code: str, race_date: date, race_number: int):
        """Get entries for a specific race"""
        date_str = race_date.strftime('%Y-%m-%d')
        meets = await self.get_meets(date_str)
        
        # Find meets for the requested track
        track_map = {
            'FM': 'FMT',  # Fair Meadows -> Fair Meadows Tulsa
            'RP': 'RP'    # Remington Park stays the same
        }
        
        actual_track_code = track_map.get(track_code, track_code)
        track_meets = [m for m in meets if m.get('track_id') == actual_track_code]
        
        if not track_meets:
            return {'entries': []}
        
        meet = track_meets[0]
        entries_data = await self.get_meet_entries(meet['meet_id'])
        
        # Find the specific race and its runners
        formatted_entries = []
        if 'races' in entries_data:
            for race in entries_data['races']:
                race_key = race.get('race_key', {})
                if int(race_key.get('race_number', 0)) == race_number:
                    runners = race.get('runners', [])
                    
                    for runner in runners:
                        # Extract jockey info
                        jockey = runner.get('jockey', {})
                        jockey_name = f"{jockey.get('first_name_initial', '')} {jockey.get('last_name', 'Unknown')}".strip()
                        
                        # Extract trainer info  
                        trainer = runner.get('trainer', {})
                        trainer_name = f"{trainer.get('first_name', '')} {trainer.get('last_name', 'Unknown')}".strip()
                        
                        # Convert weight to int
                        weight = 126
                        try:
                            weight = int(runner.get('weight', 126))
                        except (ValueError, TypeError):
                            weight = 126
                        
                        # Convert morning line odds to float
                        morning_line = 5.0
                        ml_str = runner.get('morning_line_odds', '5.0')
                        if ml_str and ml_str.strip():
                            try:
                                morning_line = float(ml_str)
                            except (ValueError, TypeError):
                                morning_line = 5.0
                        
                        formatted_entries.append({
                            'horse_registration_number': runner.get('registration_number', f"H{runner.get('program_number', 0)}"),
                            'horse_name': runner.get('horse_name', 'Unknown'),
                            'horse_age': runner.get('age', 3),
                            'jockey_id': jockey.get('id', f"J{runner.get('program_number', 0)}"),
                            'jockey_name': jockey_name,
                            'trainer_id': trainer.get('id', f"T{runner.get('program_number', 0)}"),
                            'trainer_name': trainer_name,
                            'post_position': int(runner.get('program_number', 1)),
                            'morning_line_odds': morning_line,
                            'current_odds': morning_line,  # Use morning line for current odds if no live odds
                            'weight': weight,
                            'medication': runner.get('medication', ''),
                            'equipment': runner.get('equipment', '')
                        })
                    break
        
        return {'entries': formatted_entries}
    
    async def get_race_results(self, track_code: str, race_date: date, race_number: int):
        """Get results for a specific race"""
        date_str = race_date.strftime('%Y-%m-%d')
        meets = await self.get_meets(date_str)
        
        # Find meets for the requested track
        track_map = {
            'FM': 'FMT',  # Fair Meadows -> Fair Meadows Tulsa
            'RP': 'RP'    # Remington Park stays the same
        }
        
        actual_track_code = track_map.get(track_code, track_code)
        track_meets = [m for m in meets if m.get('track_id') == actual_track_code]
        
        if not track_meets:
            return None
        
        meet = track_meets[0]
        all_results = await self.get_meet_results(meet['meet_id'])
        
        if not all_results:
            return None
        
        # Results will have similar structure to entries but with finish data
        # For now, return None since race hasn't finished yet
        # This method will need updating once we see actual results data structure
        return None
    
    # Stub methods for features not available in new API
    async def get_horse_history(self, registration_number: str):
        """Horse history not available in new API - return empty"""
        return {'performances': []}
    
    async def get_jockey_stats(self, jockey_id: str):
        """Jockey stats not available in new API - return empty"""
        return {'stats': {}}
    
    async def get_trainer_stats(self, trainer_id: str):
        """Trainer stats not available in new API - return empty"""
        return {'stats': {}}
    
    async def get_track_conditions(self, track_code: str, race_date: date):
        """Track conditions not available in new API - return default"""
        return {'condition': 'Fast', 'temperature': 72}