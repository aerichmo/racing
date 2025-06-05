from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
import asyncio
from typing import List, Dict
from pathlib import Path
from contextlib import asynccontextmanager

from database import get_db, Base, get_engine, Track, Race, Bet, BetResult, DailyROI, RaceEntry, RaceResult
from scheduler import RaceScheduler
from betting_engine import BettingEngine
import os

# Get the base directory (parent of src)
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize scheduler
scheduler = RaceScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Create database tables after environment variables are loaded
    Base.metadata.create_all(bind=get_engine())
    
    await scheduler.initialize()
    
    # Initialize tracks if not exists
    db = next(get_db())
    try:
        tracks = [
            {"name": "Remington Park", "code": "RP"},
            {"name": "Fair Meadows", "code": "FM"}
        ]
        
        for track_data in tracks:
            existing = db.query(Track).filter(Track.code == track_data["code"]).first()
            if not existing:
                track = Track(**track_data)
                db.add(track)
                
        db.commit()
    finally:
        db.close()
    
    yield
    
    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(title="Horse Racing Betting Platform", lifespan=lifespan)

# Mount static files
static_path = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    template_path = BASE_DIR / "templates" / "index.html"
    with open(template_path, "r") as f:
        return f.read()

@app.get("/api/tracks")
async def get_tracks(db: Session = Depends(get_db)):
    tracks = db.query(Track).all()
    return [{"id": t.id, "name": t.name} for t in tracks]

@app.get("/api/recommendations/{track_id}")
async def get_recommendations(track_id: int, db: Session = Depends(get_db)):
    today = date.today()
    
    # Get races for the track today
    races = db.query(Race).filter(
        Race.track_id == track_id,
        Race.race_date == today
    ).order_by(Race.race_time).all()
    
    recommendations = []
    daily_budget = 100.0
    
    for race in races:
        # Get bets for this race
        bets = db.query(Bet).filter(Bet.race_id == race.id).all()
        
        race_recommendations = []
        for bet in bets:
            entry = bet.entry
            race_recommendations.append({
                "horse_name": entry.horse.name,
                "post_position": entry.post_position,
                "current_odds": bet.odds,
                "bet_amount": bet.amount,
                "confidence": round(bet.confidence * 100, 1),
                "expected_value": round(bet.expected_value, 2),
                "percentage_of_budget": round((bet.amount / daily_budget) * 100, 1)
            })
            
        # Check if race has results
        has_results = any(entry.result for entry in race.entries)
        
        recommendations.append({
            "race_number": race.race_number,
            "race_time": race.race_time.strftime("%I:%M %p"),
            "recommendations": race_recommendations,
            "has_results": has_results,
            "race_id": race.id
        })
        
    return recommendations

@app.get("/api/race-results/{race_id}")
async def get_race_results(race_id: int, db: Session = Depends(get_db)):
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
        
    results = []
    entries = db.query(RaceEntry).filter(RaceEntry.race_id == race_id).all()
    
    for entry in entries:
        if entry.result:
            # Check if we bet on this horse
            bet = db.query(Bet).filter(
                Bet.race_id == race_id,
                Bet.entry_id == entry.id
            ).first()
            
            results.append({
                "position": entry.result.finish_position,
                "horse_name": entry.horse.name,
                "win_odds": entry.result.win_odds,
                "we_bet": bet is not None,
                "bet_amount": bet.amount if bet else 0,
                "payout": bet.result.payout if bet and hasattr(bet, 'result') and bet.result else 0
            })
            
    results.sort(key=lambda x: x["position"])
    return results

@app.get("/api/roi/{track_id}")
async def get_roi_stats(track_id: int, db: Session = Depends(get_db)):
    today = date.today()
    
    # Get expected ROI for today
    races = db.query(Race).filter(
        Race.track_id == track_id,
        Race.race_date == today
    ).all()
    
    if races:
        engine = BettingEngine(db)
        all_recommendations = []
        
        for race in races:
            bets = db.query(Bet).filter(Bet.race_id == race.id).all()
            race_recs = [{
                'bet_amount': bet.amount,
                'expected_value': bet.expected_value
            } for bet in bets]
            all_recommendations.append(race_recs)
            
        expected_roi = engine.calculate_expected_daily_roi(all_recommendations)
    else:
        expected_roi = 0
        
    # Get all-time ROI
    all_time_results = db.query(
        func.sum(DailyROI.total_wagered).label('total_wagered'),
        func.sum(DailyROI.total_returned).label('total_returned')
    ).filter(DailyROI.track_id == track_id).first()
    
    if all_time_results and all_time_results.total_wagered and all_time_results.total_wagered > 0:
        all_time_roi = ((all_time_results.total_returned - all_time_results.total_wagered) 
                       / all_time_results.total_wagered) * 100
    else:
        all_time_roi = 0
        
    # Get recent daily ROIs
    recent_rois = db.query(DailyROI).filter(
        DailyROI.track_id == track_id
    ).order_by(DailyROI.date.desc()).limit(10).all()
    
    return {
        "expected_roi_today": round(expected_roi, 2),
        "all_time_roi": round(all_time_roi, 2),
        "recent_daily_rois": [
            {
                "date": roi.date.strftime("%m/%d"),
                "roi": round(roi.roi_percentage, 2)
            } for roi in recent_rois
        ]
    }

@app.post("/api/sync/initial")
async def trigger_initial_sync(db: Session = Depends(get_db)):
    """Manual trigger for initial sync"""
    await scheduler.run_initial_sync()
    return {"status": "Initial sync completed"}

@app.post("/api/sync/pre-race")
async def trigger_pre_race_sync(db: Session = Depends(get_db)):
    """Manual trigger for pre-race sync"""
    await scheduler.run_pre_race_sync()
    return {"status": "Pre-race sync completed"}

@app.post("/api/sync/force-fair-meadows")
async def force_sync_fair_meadows(db: Session = Depends(get_db)):
    """Force sync Fair Meadows races immediately"""
    from data_sync import DataSync
    sync = DataSync()
    await sync.sync_initial_data(db)
    return {"status": "Fair Meadows sync completed"}

@app.post("/api/cleanup/races")
async def cleanup_races(db: Session = Depends(get_db)):
    """Delete all race data for today"""
    today = date.today()
    
    # Delete in proper order due to foreign key constraints
    db.query(Bet).filter(Race.race_date == today).delete(synchronize_session=False)
    db.query(RaceEntry).filter(Race.race_date == today).delete(synchronize_session=False) 
    db.query(Race).filter(Race.race_date == today).delete(synchronize_session=False)
    
    db.commit()
    return {"status": f"Deleted all race data for {today}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)