from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta, date
import asyncio
from sqlalchemy.orm import Session
from database import get_db, Race, Track
from data_sync import DataSync
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RaceScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.data_sync = DataSync()
        
    async def initialize(self):
        # Schedule daily 8 AM sync
        self.scheduler.add_job(
            self.run_initial_sync,
            CronTrigger(hour=8, minute=0),
            id='daily_sync',
            replace_existing=True
        )
        
        # Schedule dynamic pre-race syncs
        self.scheduler.add_job(
            self.schedule_race_syncs,
            CronTrigger(hour=8, minute=30),
            id='schedule_races',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Scheduler initialized")
        
    async def run_initial_sync(self):
        logger.info("Running 8 AM initial sync")
        db = next(get_db())
        try:
            await self.data_sync.sync_initial_data(db)
            await self.schedule_race_syncs()
        finally:
            db.close()
            
    async def schedule_race_syncs(self):
        """Schedule pre-race syncs based on today's races"""
        db = next(get_db())
        try:
            today = date.today()
            
            # Get all races for today
            races = db.query(Race).filter(Race.race_date == today).order_by(Race.race_time).all()
            
            if races:
                # Schedule 1 hour before first race
                first_race_time = races[0].race_time
                pre_race_time = first_race_time - timedelta(hours=1)
                
                if pre_race_time > datetime.now():
                    self.scheduler.add_job(
                        self.run_pre_race_sync,
                        DateTrigger(run_date=pre_race_time),
                        id='pre_race_sync',
                        replace_existing=True
                    )
                    logger.info(f"Scheduled pre-race sync at {pre_race_time}")
                
                # Schedule 10 minutes before each race
                for race in races:
                    update_time = race.race_time - timedelta(minutes=10)
                    
                    if update_time > datetime.now():
                        self.scheduler.add_job(
                            self.run_race_update,
                            DateTrigger(run_date=update_time),
                            args=[race.id],
                            id=f'race_update_{race.id}',
                            replace_existing=True
                        )
                        logger.info(f"Scheduled update for race {race.race_number} at {update_time}")
                        
                
        finally:
            db.close()
            
    async def run_pre_race_sync(self):
        logger.info("Running pre-race sync")
        db = next(get_db())
        try:
            await self.data_sync.sync_pre_race_data(db)
        finally:
            db.close()
            
    async def run_race_update(self, race_id: int):
        logger.info(f"Running race update for race {race_id}")
        db = next(get_db())
        try:
            await self.data_sync.sync_race_updates(db, race_id)
        finally:
            db.close()
            
    
