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
        # Map internal track codes to API track codes
        track_map = {
            'FM': 'FMT',  # Fair Meadows -> Fair Meadows Tulsa
            'RP': 'RP'    # Remington Park stays the same
        }
        api_track_code = track_map.get(track_code, track_code)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/meets/{api_track_code}/{race_date.strftime('%Y-%m-%d')}",
                headers=self.auth_header
            )
            response.raise_for_status()
            return response.json()
    
    async def get_race_entries(self, track_code: str, race_date: date, race_number: int):
        # Map internal track codes to API track codes
        track_map = {
            'FM': 'FMT',  # Fair Meadows -> Fair Meadows Tulsa
            'RP': 'RP'    # Remington Park stays the same
        }
        api_track_code = track_map.get(track_code, track_code)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/entries/{api_track_code}/{race_date.strftime('%Y-%m-%d')}/{race_number}",
                headers=self.auth_header
            )
            response.raise_for_status()
            return response.json()
    
    async def get_race_results(self, track_code: str, race_date: date, race_number: int):
        # Map internal track codes to API track codes
        track_map = {
            'FM': 'FMT',  # Fair Meadows -> Fair Meadows Tulsa
            'RP': 'RP'    # Remington Park stays the same
        }
        api_track_code = track_map.get(track_code, track_code)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/v1/results/{api_track_code}/{race_date.strftime('%Y-%m-%d')}/{race_number}",
                    headers=self.auth_header
                )
                response.raise_for_status()
                return response.json()
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