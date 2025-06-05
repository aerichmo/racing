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
                
                for race_info in races_data.get('races', []):
                    await self._sync_race(db, track.id, race_info, today)
                    
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
    
    async def _sync_race(self, db: Session, track_id: int, race_info: dict, race_date: date):
        # Check if race already exists
        race_key = race_info.get('race_key', '')
        existing_race = db.query(Race).filter(
            Race.api_id == race_key,
            Race.track_id == track_id
        ).first()
        
        if not existing_race:
            # Extract race number from race_key (format: "R1", "R2", etc.)
            race_key = race_info.get('race_key', '')
            race_number = int(race_key.replace('R', '')) if race_key.startswith('R') else 1
            
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
                api_id=race_info.get('race_key', ''),
                track_id=track_id,
                race_number=race_number,
                race_date=race_date,
                race_time=race_time,
                distance=race_info.get('distance_value', 0),
                surface=race_info.get('surface_description', ''),
                race_type=race_info.get('race_type', ''),
                purse=race_info.get('purse', 0),
                conditions=race_info.get('race_restriction_description', ''),
                track_name=track_name
            )
            db.add(race)
            
    async def _sync_entries(self, db: Session, race_id: int, entries_data: dict):
        for entry_info in entries_data.get('entries', []):
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
                entry = RaceEntry(
                    race_id=race_id,
                    horse_id=horse.id,
                    jockey_id=jockey.id,
                    trainer_id=trainer.id,
                    post_position=entry_info.get('post_position'),
                    morning_line_odds=entry_info.get('morning_line_odds', 0),
                    current_odds=entry_info.get('current_odds', entry_info.get('morning_line_odds', 0)),
                    weight=entry_info.get('weight'),
                    medication=entry_info.get('medication'),
                    equipment=entry_info.get('equipment')
                )
                db.add(entry)
                
    async def _get_or_create_horse(self, db: Session, entry_info: dict) -> Horse:
        reg_number = entry_info.get('horse_registration_number')
        horse = db.query(Horse).filter(Horse.registration_number == reg_number).first()
        
        if not horse:
            horse = Horse(
                registration_number=reg_number,
                name=entry_info.get('horse_name'),
                age=entry_info.get('horse_age')
            )
            db.add(horse)
            db.flush()
            
        return horse
    
    async def _get_or_create_jockey(self, db: Session, entry_info: dict) -> Jockey:
        jockey_id = entry_info.get('jockey_id')
        jockey = db.query(Jockey).filter(Jockey.api_id == jockey_id).first()
        
        if not jockey:
            jockey = Jockey(
                api_id=jockey_id,
                name=entry_info.get('jockey_name')
            )
            db.add(jockey)
            db.flush()
            
        return jockey
    
    async def _get_or_create_trainer(self, db: Session, entry_info: dict) -> Trainer:
        trainer_id = entry_info.get('trainer_id')
        trainer = db.query(Trainer).filter(Trainer.api_id == trainer_id).first()
        
        if not trainer:
            trainer = Trainer(
                api_id=trainer_id,
                name=entry_info.get('trainer_name')
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
                        track_name=perf.get('track_name'),
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