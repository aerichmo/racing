from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

# Load .env file if it exists, but allow environment variables to override
load_dotenv(override=False)

# Also try loading from parent directory (where .env typically is)
from pathlib import Path
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=False)

# Create engine lazily to avoid issues during import
engine = None
SessionLocal = None

def get_engine():
    global engine
    if engine is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise ValueError(
                "DATABASE_URL environment variable is not set. "
                "Please set it in your Render dashboard under Environment Variables."
            )
        engine = create_engine(DATABASE_URL)
    return engine

def get_session_local():
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal

Base = declarative_base()

class Track(Base):
    __tablename__ = "tracks"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    code = Column(String, unique=True)
    
class Horse(Base):
    __tablename__ = "horses"
    
    id = Column(Integer, primary_key=True)
    registration_number = Column(String, unique=True, index=True)
    name = Column(String)
    age = Column(Integer)
    
class Jockey(Base):
    __tablename__ = "jockeys"
    
    id = Column(Integer, primary_key=True)
    api_id = Column(String, unique=True, index=True)
    name = Column(String)
    
class Trainer(Base):
    __tablename__ = "trainers"
    
    id = Column(Integer, primary_key=True)
    api_id = Column(String, unique=True, index=True)
    name = Column(String)

class Race(Base):
    __tablename__ = "races"
    
    id = Column(Integer, primary_key=True)
    api_id = Column(String, unique=True, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"))
    race_number = Column(Integer)
    race_date = Column(Date)
    race_time = Column(DateTime)
    distance = Column(Float)
    surface = Column(String)
    race_type = Column(String)
    purse = Column(Float)
    conditions = Column(Text)
    
    track = relationship("Track")
    entries = relationship("RaceEntry", back_populates="race")
    
class RaceEntry(Base):
    __tablename__ = "race_entries"
    
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.id"))
    horse_id = Column(Integer, ForeignKey("horses.id"))
    jockey_id = Column(Integer, ForeignKey("jockeys.id"))
    trainer_id = Column(Integer, ForeignKey("trainers.id"))
    post_position = Column(Integer)
    morning_line_odds = Column(Float)
    current_odds = Column(Float)
    weight = Column(Float)
    medication = Column(String)
    equipment = Column(String)
    
    race = relationship("Race", back_populates="entries")
    horse = relationship("Horse")
    jockey = relationship("Jockey")
    trainer = relationship("Trainer")
    result = relationship("RaceResult", uselist=False, back_populates="entry")
    
class RaceResult(Base):
    __tablename__ = "race_results"
    
    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, ForeignKey("race_entries.id"), unique=True)
    finish_position = Column(Integer)
    win_odds = Column(Float)
    place_odds = Column(Float)
    show_odds = Column(Float)
    margin = Column(Float)
    time = Column(Float)
    
    entry = relationship("RaceEntry", back_populates="result")
    
class HistoricalPerformance(Base):
    __tablename__ = "historical_performances"
    
    id = Column(Integer, primary_key=True)
    horse_id = Column(Integer, ForeignKey("horses.id"))
    jockey_id = Column(Integer, ForeignKey("jockeys.id"))
    trainer_id = Column(Integer, ForeignKey("trainers.id"))
    race_date = Column(Date)
    distance = Column(Float)
    surface = Column(String)
    finish_position = Column(Integer)
    beaten_lengths = Column(Float)
    odds = Column(Float)
    speed_figure = Column(Float)
    
    horse = relationship("Horse")
    jockey = relationship("Jockey")
    trainer = relationship("Trainer")

class Bet(Base):
    __tablename__ = "bets"
    
    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.id"))
    entry_id = Column(Integer, ForeignKey("race_entries.id"))
    bet_type = Column(String)
    amount = Column(Float)
    odds = Column(Float)
    confidence = Column(Float)
    expected_value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    
    race = relationship("Race")
    entry = relationship("RaceEntry")
    result = relationship("BetResult", uselist=False, back_populates="bet")
    
class BetResult(Base):
    __tablename__ = "bet_results"
    
    id = Column(Integer, primary_key=True)
    bet_id = Column(Integer, ForeignKey("bets.id"), unique=True)
    won = Column(Boolean)
    payout = Column(Float)
    processed_at = Column(DateTime, server_default=func.now())
    
    bet = relationship("Bet", back_populates="result")
    
class DailyROI(Base):
    __tablename__ = "daily_roi"
    
    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey("tracks.id"))
    date = Column(Date)
    total_wagered = Column(Float)
    total_returned = Column(Float)
    roi_percentage = Column(Float)
    
    track = relationship("Track")

def get_db():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()