from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta, date
import asyncio
from sqlalchemy.orm import Session
from database import get_db, Race, Bet, BetResult, DailyROI, Track
from data_sync import DataSync
from betting_engine import BettingEngine
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
                        
                # Schedule results check after last race
                last_race_time = races[-1].race_time + timedelta(minutes=30)
                self.scheduler.add_job(
                    self.process_daily_results,
                    DateTrigger(run_date=last_race_time),
                    id='daily_results',
                    replace_existing=True
                )
                
        finally:
            db.close()
            
    async def run_pre_race_sync(self):
        logger.info("Running pre-race sync and generating recommendations")
        db = next(get_db())
        try:
            await self.data_sync.sync_pre_race_data(db)
            await self.generate_daily_recommendations(db)
        finally:
            db.close()
            
    async def run_race_update(self, race_id: int):
        logger.info(f"Running race update for race {race_id}")
        db = next(get_db())
        try:
            await self.data_sync.sync_race_updates(db, race_id)
            await self.generate_race_recommendations(db, race_id)
        finally:
            db.close()
            
    async def generate_daily_recommendations(self, db: Session):
        """Generate betting recommendations for all races"""
        logger.info("Generating daily betting recommendations")
        
        engine = BettingEngine(db)
        today = date.today()
        
        # Get all races for today
        races = db.query(Race).filter(Race.race_date == today).order_by(Race.race_time).all()
        
        all_recommendations = []
        
        for race in races:
            recommendations = await engine.analyze_race(race)
            
            # Save bets to database
            for rec in recommendations:
                bet = Bet(
                    race_id=race.id,
                    entry_id=rec['entry_id'],
                    bet_type=rec['bet_type'],
                    amount=rec['bet_amount'],
                    odds=rec['current_odds'],
                    confidence=rec['confidence'],
                    expected_value=rec['expected_value']
                )
                db.add(bet)
                
            all_recommendations.append(recommendations)
            
        # Calculate expected ROI
        expected_roi = engine.calculate_expected_daily_roi(all_recommendations)
        logger.info(f"Expected daily ROI: {expected_roi:.2f}%")
        
        db.commit()
        
    async def generate_race_recommendations(self, db: Session, race_id: int):
        """Update recommendations for a specific race with latest odds"""
        logger.info(f"Updating recommendations for race {race_id}")
        
        engine = BettingEngine(db)
        race = db.query(Race).filter(Race.id == race_id).first()
        
        if race:
            # Delete old recommendations
            db.query(Bet).filter(Bet.race_id == race_id).delete()
            
            # Generate new recommendations
            recommendations = await engine.analyze_race(race)
            
            for rec in recommendations:
                bet = Bet(
                    race_id=race.id,
                    entry_id=rec['entry_id'],
                    bet_type=rec['bet_type'],
                    amount=rec['bet_amount'],
                    odds=rec['current_odds'],
                    confidence=rec['confidence'],
                    expected_value=rec['expected_value']
                )
                db.add(bet)
                
            db.commit()
            
    async def process_daily_results(self):
        """Process all bet results and calculate daily ROI"""
        logger.info("Processing daily results")
        
        db = next(get_db())
        try:
            today = date.today()
            
            # Get all bets for today
            bets = db.query(Bet).join(Race).filter(Race.race_date == today).all()
            
            for bet in bets:
                if not hasattr(bet, 'result') or not bet.result:
                    # Check if race has results
                    entry = bet.entry
                    if entry.result:
                        won = entry.result.finish_position == 1
                        payout = bet.amount * (bet.odds + 1) if won else 0
                        
                        bet_result = BetResult(
                            bet_id=bet.id,
                            won=won,
                            payout=payout
                        )
                        db.add(bet_result)
                        
            # Calculate daily ROI for each track
            for track_name in ["Remington Park", "Fair Meadows"]:
                track = db.query(Track).filter(Track.name == track_name).first()
                if track:
                    track_bets = db.query(Bet).join(Race).filter(
                        Race.track_id == track.id,
                        Race.race_date == today
                    ).all()
                    
                    total_wagered = sum(bet.amount for bet in track_bets)
                    total_returned = sum(
                        bet.result.payout for bet in track_bets 
                        if hasattr(bet, 'result') and bet.result
                    )
                    
                    if total_wagered > 0:
                        roi_percentage = ((total_returned - total_wagered) / total_wagered) * 100
                        
                        daily_roi = DailyROI(
                            track_id=track.id,
                            date=today,
                            total_wagered=total_wagered,
                            total_returned=total_returned,
                            roi_percentage=roi_percentage
                        )
                        db.add(daily_roi)
                        
            db.commit()
            logger.info("Daily results processed successfully")
            
        finally:
            db.close()