import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import (
    Track, Horse, Jockey, Trainer, Race, RaceEntry, 
    RaceResult, HistoricalPerformance, get_db
)
from racing_api import RacingAPIClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSync:
    def __init__(self):
        self.api_client = RacingAPIClient()
        self.track_codes = {
            "Remington Park": "RP",
            "Fair Meadows": "FM"
        }
        
    async def sync_initial_data(self, db: Session):
        """8 AM sync - get all races for the day"""
        logger.info("Starting 8 AM initial data sync")
        
        for track_name, track_code in self.track_codes.items():
            # Ensure track exists in database
            track = db.query(Track).filter(Track.code == track_code).first()
            if not track:
                track = Track(name=track_name, code=track_code)
                db.add(track)
                db.commit()
            
            # Get today's races
            today = date.today()
            try:
                races_data = await self.api_client.get_races_by_date(track_code, today)
                
                # Group entries by race_number to identify unique races
                races_by_number = {}
                for entry in races_data.get('entries', []):
                    race_num = entry.get('race_number', 0)
                    if race_num not in races_by_number:
                        races_by_number[race_num] = entry
                
                for race_number, race_info in races_by_number.items():
                    await self._sync_race(db, track.id, race_info, today, race_number)
                    
            except Exception as e:
                logger.error(f"Error syncing races for {track_name}: {e}")
                
        db.commit()
        logger.info("Initial data sync completed")
    
    async def sync_pre_race_data(self, db: Session):
        """1 hour before first race - sync entries and calculate odds"""
        logger.info("Starting pre-race data sync")
        
        today = date.today()
        
        for track_name, track_code in self.track_codes.items():
            track = db.query(Track).filter(Track.code == track_code).first()
            if not track:
                continue
                
            # Get today's races
            races = db.query(Race).filter(
                Race.track_id == track.id,
                Race.race_date == today
            ).all()
            
            for race in races:
                try:
                    # Sync entries for each race
                    entries_data = await self.api_client.get_race_entries(
                        track_code, today, race.race_number
                    )
                    
                    await self._sync_entries(db, race.id, entries_data)
                    
                    # Sync historical data for each horse/jockey/trainer
                    entries = db.query(RaceEntry).filter(RaceEntry.race_id == race.id).all()
                    
                    for entry in entries:
                        await self._sync_historical_data(db, entry)
                        
                except Exception as e:
                    logger.error(f"Error syncing entries for race {race.race_number}: {e}")
                    
        db.commit()
        logger.info("Pre-race data sync completed")
    
    async def sync_race_updates(self, db: Session, race_id: int):
        """10 minutes before each race - update odds and sync previous results"""
        logger.info(f"Starting race update sync for race {race_id}")
        
        race = db.query(Race).filter(Race.id == race_id).first()
        if not race:
            return
            
        track = race.track
        
        try:
            # Update current odds
            entries_data = await self.api_client.get_race_entries(
                track.code, race.race_date, race.race_number
            )
            
            await self._update_current_odds(db, race.id, entries_data)
            
            # Sync results from previous race if exists
            if race.race_number > 1:
                prev_race = db.query(Race).filter(
                    Race.track_id == track.id,
                    Race.race_date == race.race_date,
                    Race.race_number == race.race_number - 1
                ).first()
                
                if prev_race:
                    await self._sync_race_results(db, prev_race, track.code)
                    
        except Exception as e:
            logger.error(f"Error updating race {race_id}: {e}")
            
        db.commit()
        logger.info(f"Race update sync completed for race {race_id}")
    
    async def _sync_race(self, db: Session, track_id: int, race_info: dict, race_date: date, race_number: int):
        # Create race_key from race_number
        race_key = f"R{race_number}"
        existing_race = db.query(Race).filter(
            Race.api_id == race_key,
            Race.track_id == track_id
        ).first()
        
        if not existing_race:
            # Parse post time
            post_time_str = race_info.get('post_time', '')
            if post_time_str:
                try:
                    race_time = datetime.fromisoformat(post_time_str.replace('Z', '+00:00'))
                except:
                    race_time = datetime.now()
            else:
                race_time = datetime.now()
            
            # Get track name
            track = db.query(Track).filter(Track.id == track_id).first()
            track_name = track.name if track else ""
            
            race = Race(
                api_id=race_key,
                track_id=track_id,
                race_number=race_number,
                race_date=race_date,
                race_time=race_time,
                distance=race_info.get('distance_value', 0),
                surface=race_info.get('surface_description', ''),
                race_type=race_info.get('race_type', ''),
                purse=race_info.get('purse', 0),
                conditions=race_info.get('race_restriction_description', '')
            )
            db.add(race)
            
    async def _sync_entries(self, db: Session, race_id: int, entries_data: dict):
        # Handle both 'entries' and 'runners' formats (Fair Meadows uses 'runners')
        entries_list = entries_data.get('entries', []) or entries_data.get('runners', [])
        
        logger.info(f"Processing {len(entries_list)} entries for race {race_id}")
        
        for entry_info in entries_list:
            try:
                # Sync horse
                horse = await self._get_or_create_horse(db, entry_info)
                
                # Sync jockey
                jockey = await self._get_or_create_jockey(db, entry_info)
                
                # Sync trainer
                trainer = await self._get_or_create_trainer(db, entry_info)
                
                # Check if entry exists
                existing_entry = db.query(RaceEntry).filter(
                    RaceEntry.race_id == race_id,
                    RaceEntry.horse_id == horse.id
                ).first()
                
                if not existing_entry:
                    # Handle different field names for different APIs
                    post_pos = (entry_info.get('post_position') or 
                               entry_info.get('post_pos') or 
                               entry_info.get('program_number') or
                               entry_info.get('cloth_number'))
                    
                    # Handle morning line odds
                    morning_odds = (entry_info.get('morning_line_odds') or
                                   entry_info.get('odds') or
                                   entry_info.get('ml_odds'))
                    
                    if isinstance(morning_odds, str):
                        # Convert "12-1" to decimal odds
                        try:
                            if '-' in morning_odds:
                                parts = morning_odds.split('-')
                                if len(parts) == 2:
                                    morning_odds = float(parts[0]) / float(parts[1]) + 1
                            else:
                                morning_odds = float(morning_odds)
                        except:
                            morning_odds = 3.0  # Default odds
                    elif not morning_odds:
                        morning_odds = 3.0  # Default odds
                    
                    # Handle weight
                    weight = entry_info.get('weight') or entry_info.get('jockey_weight') or 126
                    
                    entry = RaceEntry(
                        race_id=race_id,
                        horse_id=horse.id,
                        jockey_id=jockey.id,
                        trainer_id=trainer.id,
                        post_position=post_pos,
                        morning_line_odds=morning_odds,
                        current_odds=entry_info.get('current_odds', morning_odds),
                        weight=weight,
                        medication=entry_info.get('medication'),
                        equipment=entry_info.get('equipment')
                    )
                    db.add(entry)
                    logger.info(f"Added entry for horse {horse.name} in race {race_id}")
                    
            except Exception as e:
                logger.error(f"Error processing entry in race {race_id}: {e}")
                continue
                
    async def _get_or_create_horse(self, db: Session, entry_info: dict) -> Horse:
        # Handle different API field names
        reg_number = (entry_info.get('horse_registration_number') or 
                     entry_info.get('registration_number') or
                     entry_info.get('horse_id'))
        
        # Handle horse name from different sources
        horse_name = (entry_info.get('horse_name') or
                     entry_info.get('name'))
        
        # For Fair Meadows, horse data might be nested
        if 'horse' in entry_info and isinstance(entry_info['horse'], dict):
            horse_data = entry_info['horse']
            reg_number = reg_number or horse_data.get('registration_number') or horse_data.get('id')
            horse_name = horse_name or horse_data.get('name')
        
        # Generate fallback if no registration number
        if not reg_number:
            reg_number = f"TEMP_{hash(horse_name or 'unknown') % 100000}"
        
        horse = db.query(Horse).filter(Horse.registration_number == reg_number).first()
        
        if not horse:
            horse = Horse(
                registration_number=reg_number,
                name=horse_name or f"Horse {reg_number}",
                age=entry_info.get('horse_age') or entry_info.get('age') or 4
            )
            db.add(horse)
            db.flush()
            
        return horse
    
    async def _get_or_create_jockey(self, db: Session, entry_info: dict) -> Jockey:
        # Handle different API formats - jockey can be ID or object
        jockey_data = entry_info.get('jockey')
        
        if isinstance(jockey_data, dict):
            # Fair Meadows format: {"id": "jky_na_474639", "first_name": "Gonzalo", "last_name": "Gutierrez"}
            jockey_id = jockey_data.get('id')
            jockey_name = f"{jockey_data.get('first_name', '')} {jockey_data.get('last_name', '')}".strip()
        else:
            # Standard format
            jockey_id = entry_info.get('jockey_id') or jockey_data
            jockey_name = entry_info.get('jockey_name')
        
        jockey = db.query(Jockey).filter(Jockey.api_id == jockey_id).first()
        
        if not jockey:
            jockey = Jockey(
                api_id=jockey_id,
                name=jockey_name
            )
            db.add(jockey)
            db.flush()
            
        return jockey
    
    async def _get_or_create_trainer(self, db: Session, entry_info: dict) -> Trainer:
        # Handle different API formats - trainer can be ID or object
        trainer_data = entry_info.get('trainer')
        
        if isinstance(trainer_data, dict):
            # Fair Meadows format: {"id": "trn_na_56727", "first_name": "James", "last_name": "Goodnight"}
            trainer_id = trainer_data.get('id')
            trainer_name = f"{trainer_data.get('first_name', '')} {trainer_data.get('last_name', '')}".strip()
        else:
            # Standard format
            trainer_id = entry_info.get('trainer_id') or trainer_data
            trainer_name = entry_info.get('trainer_name')
        
        trainer = db.query(Trainer).filter(Trainer.api_id == trainer_id).first()
        
        if not trainer:
            trainer = Trainer(
                api_id=trainer_id,
                name=trainer_name
            )
            db.add(trainer)
            db.flush()
            
        return trainer
    
    async def _sync_historical_data(self, db: Session, entry: RaceEntry):
        # Get horse history
        try:
            history_data = await self.api_client.get_horse_history(entry.horse.registration_number)
            
            for perf in history_data.get('performances', [])[-20:]:  # Last 20 races
                existing_perf = db.query(HistoricalPerformance).filter(
                    HistoricalPerformance.horse_id == entry.horse_id,
                    HistoricalPerformance.race_date == date.fromisoformat(perf.get('race_date'))
                ).first()
                
                if not existing_perf:
                    hist_perf = HistoricalPerformance(
                        horse_id=entry.horse_id,
                        jockey_id=entry.jockey_id if perf.get('jockey_id') == entry.jockey.api_id else None,
                        trainer_id=entry.trainer_id if perf.get('trainer_id') == entry.trainer.api_id else None,
                        race_date=date.fromisoformat(perf.get('race_date')),
                        distance=perf.get('distance'),
                        surface=perf.get('surface'),
                        finish_position=perf.get('finish_position'),
                        beaten_lengths=perf.get('beaten_lengths', 0),
                        odds=perf.get('odds'),
                        speed_figure=perf.get('speed_figure')
                    )
                    db.add(hist_perf)
                    
        except Exception as e:
            logger.error(f"Error syncing historical data for horse {entry.horse.name}: {e}")
            
    async def _update_current_odds(self, db: Session, race_id: int, entries_data: dict):
        for entry_info in entries_data.get('entries', []):
            reg_number = entry_info.get('horse_registration_number')
            
            horse = db.query(Horse).filter(Horse.registration_number == reg_number).first()
            if horse:
                entry = db.query(RaceEntry).filter(
                    RaceEntry.race_id == race_id,
                    RaceEntry.horse_id == horse.id
                ).first()
                
                if entry:
                    entry.current_odds = entry_info.get('current_odds', entry.current_odds)
                    
    async def _sync_race_results(self, db: Session, race: Race, track_code: str):
        try:
            results_data = await self.api_client.get_race_results(
                track_code, race.race_date, race.race_number
            )
            
            if results_data:
                for result_info in results_data.get('results', []):
                    reg_number = result_info.get('horse_registration_number')
                    
                    horse = db.query(Horse).filter(Horse.registration_number == reg_number).first()
                    if horse:
                        entry = db.query(RaceEntry).filter(
                            RaceEntry.race_id == race.id,
                            RaceEntry.horse_id == horse.id
                        ).first()
                        
                        if entry and not entry.result:
                            result = RaceResult(
                                entry_id=entry.id,
                                finish_position=result_info.get('finish_position'),
                                win_odds=result_info.get('win_odds'),
                                place_odds=result_info.get('place_odds'),
                                show_odds=result_info.get('show_odds'),
                                margin=result_info.get('margin'),
                                time=result_info.get('time')
                            )
                            db.add(result)
                            
        except Exception as e:
            logger.error(f"Error syncing results for race {race.race_number}: {e}")