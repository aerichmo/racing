#!/usr/bin/env python3
import os
import sys
from datetime import datetime, date, time, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import random

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import Track, Race, Horse, Jockey, Trainer, RaceEntry

load_dotenv()

# Create database connection
engine = create_engine(os.getenv('DATABASE_URL'))
Session = sessionmaker(bind=engine)
db = Session()

def add_test_races():
    """Add test races for Fair Meadows"""
    
    # Get Fair Meadows track
    fm_track = db.query(Track).filter(Track.code == 'FM').first()
    if not fm_track:
        print("Fair Meadows track not found!")
        return
    
    print(f"Found Fair Meadows track with ID: {fm_track.id}")
    
    # Create test horses
    test_horses = []
    for i in range(1, 21):
        horse = db.query(Horse).filter(Horse.registration_number == f"FM2025{i:03d}").first()
        if not horse:
            horse = Horse(
                registration_number=f"FM2025{i:03d}",
                name=f"Fair Meadows Star {i}",
                age=random.randint(3, 8)
            )
            db.add(horse)
        test_horses.append(horse)
    
    # Create test jockeys
    test_jockeys = []
    for i in range(1, 11):
        jockey = db.query(Jockey).filter(Jockey.api_id == f"FM_J{i}").first()
        if not jockey:
            jockey = Jockey(
                api_id=f"FM_J{i}",
                name=f"J. Rider{i}"
            )
            db.add(jockey)
        test_jockeys.append(jockey)
    
    # Create test trainers
    test_trainers = []
    for i in range(1, 8):
        trainer = db.query(Trainer).filter(Trainer.api_id == f"FM_T{i}").first()
        if not trainer:
            trainer = Trainer(
                api_id=f"FM_T{i}",
                name=f"T. Coach{i}"
            )
            db.add(trainer)
        test_trainers.append(trainer)
    
    db.commit()
    
    # Create races for today
    today = date.today()
    base_time = datetime.combine(today, time(13, 0))  # Start at 1:00 PM
    
    # Create 8 races
    for race_num in range(1, 9):
        race_time = base_time + timedelta(minutes=30 * (race_num - 1))
        
        # Check if race already exists
        existing_race = db.query(Race).filter(
            Race.track_id == fm_track.id,
            Race.race_date == today,
            Race.race_number == race_num
        ).first()
        
        if not existing_race:
            race = Race(
                api_id=f"FM_{today}_{race_num}",
                track_id=fm_track.id,
                race_number=race_num,
                race_date=today,
                race_time=race_time,
                distance="6 furlongs",
                surface="Dirt",
                race_type="Claiming",
                purse=25000,
                conditions="3yo+ claiming $10,000"
            )
            db.add(race)
            db.commit()
            
            # Add 8-10 horses to each race
            num_horses = random.randint(8, 10)
            selected_horses = random.sample(test_horses, num_horses)
            
            for post_pos, horse in enumerate(selected_horses, 1):
                jockey = random.choice(test_jockeys)
                trainer = random.choice(test_trainers)
                
                entry = RaceEntry(
                    race_id=race.id,
                    horse_id=horse.id,
                    jockey_id=jockey.id,
                    trainer_id=trainer.id,
                    post_position=post_pos,
                    morning_line_odds=random.uniform(2.0, 20.0),
                    current_odds=random.uniform(2.0, 20.0),
                    weight=126,
                    medication="L",
                    equipment="b"
                )
                db.add(entry)
            
            print(f"Added race {race_num} at {race_time.strftime('%I:%M %p')} with {num_horses} horses")
        else:
            print(f"Race {race_num} already exists")
    
    db.commit()
    print("\nTest data added successfully!")

if __name__ == "__main__":
    add_test_races()
    db.close()