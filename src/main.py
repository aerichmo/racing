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

@app.get("/api/races/{track_id}")
async def get_races(track_id: int, db: Session = Depends(get_db)):
    today = date.today()
    
    # Get races for the track today
    races = db.query(Race).filter(
        Race.track_id == track_id,
        Race.race_date == today
    ).order_by(Race.race_time).all()
    
    race_list = []
    
    for race in races:
        race_info = {
            "race_number": race.race_number,
            "race_name": race.conditions or f"Race {race.race_number}",
            "race_time": race.race_time.strftime("%I:%M %p"),
            "distance": f"{race.distance} {race.surface}" if race.distance else "Unknown distance",
            "race_type": race.race_type or "Unknown",
            "purse": f"${race.purse:,.0f}" if race.purse else "Unknown",
            "horses": []
        }
        
        # Get horses for this race (simplified, avoiding complex relationships)
        try:
            # Simple approach - just show that horses exist
            race_info["horses"] = ["Horses will be loaded in next layer"]
        except Exception:
            race_info["horses"] = []
        
        race_list.append(race_info)
        
    return race_list

@app.get("/api/recommendations/{track_id}")
async def get_recommendations(track_id: int, db: Session = Depends(get_db)):
    try:
        today = date.today()
        
        # Check if track exists
        track = db.query(Track).filter(Track.id == track_id).first()
        if not track:
            return {"error": "Track not found", "recommendations": []}
        
        # Get races for the track today
        races = db.query(Race).filter(
            Race.track_id == track_id,
            Race.race_date == today
        ).order_by(Race.race_time).all()
        
        if not races:
            return {
                "message": f"No races scheduled for {track.name} today",
                "recommendations": [],
                "track_name": track.name,
                "date": today.strftime("%Y-%m-%d")
            }
        
        recommendations = []
        daily_budget = 100.0
        
        for race in races:
            # Get bets for this race
            bets = db.query(Bet).filter(Bet.race_id == race.id).all()
            
            race_recommendations = []
            for bet in bets:
                entry = bet.entry
                if entry and entry.horse:  # Ensure entry and horse exist
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
            has_results = any(entry.result for entry in race.entries if entry)
            
            recommendations.append({
                "race_number": race.race_number,
                "race_time": race.race_time.strftime("%I:%M %p"),
                "recommendations": race_recommendations,
                "has_results": has_results,
                "race_id": race.id
            })
            
        return {"recommendations": recommendations, "track_name": track.name}
    except Exception as e:
        print(f"Error in get_recommendations: {e}")
        return {"error": str(e), "recommendations": []}

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

@app.post("/api/sync/manual")
async def trigger_manual_sync(db: Session = Depends(get_db)):
    """Manual sync - simplified direct approach"""
    try:
        from data_sync import DataSync
        from racing_api import RacingAPIClient
        
        api_client = RacingAPIClient()
        today = date.today()
        
        # Get both tracks
        tracks = [
            {"name": "Remington Park", "code": "RP"},
            {"name": "Fair Meadows", "code": "FM"}
        ]
        
        total_races_synced = 0
        debug_info = []
        
        for track_data in tracks:
            track = db.query(Track).filter(Track.name == track_data["name"]).first()
            if not track:
                debug_info.append(f"{track_data['name']} track not found in database")
                continue
            
            # Get races directly from API
            races_data = await api_client.get_races_by_date(track_data["code"], today)
            
            races_synced = 0
            track_debug = [f"{track_data['name']} - API response keys: {list(races_data.keys()) if races_data else 'None'}"]
            track_debug.append(f"{track_data['name']} - Entries in response: {len(races_data.get('entries', []))} if races_data else 0")
            
            # Group entries by race_number to identify unique races
            races_by_number = {}
            for entry in races_data.get('entries', []):
                race_num = entry.get('race_number', 0)
                if race_num not in races_by_number:
                    races_by_number[race_num] = entry
            
            track_debug.append(f"{track_data['name']} - Unique races found: {len(races_by_number)}")
            
            for race_number, race_info in races_by_number.items():
                # Use race_number as the key since entries don't have race_key
                race_key = f"R{race_number}"
                track_debug.append(f"{track_data['name']} Race {race_number}: Creating race_key={race_key}")
                
                # Check if already exists
                existing = db.query(Race).filter(
                    Race.api_id == race_key,
                    Race.track_id == track.id
                ).first()
                
                if not existing:
                    # Parse post time
                    post_time_str = race_info.get('post_time', '')
                    if post_time_str:
                        try:
                            race_time = datetime.fromisoformat(post_time_str.replace('Z', '+00:00'))
                        except:
                            race_time = datetime.now()
                    else:
                        race_time = datetime.now()
                    
                    race = Race(
                        api_id=race_key,
                        track_id=track.id,
                        race_number=race_number,
                        race_date=today,
                        race_time=race_time,
                        distance=race_info.get('distance_value', 0),
                        surface=race_info.get('surface_description', ''),
                        race_type=race_info.get('race_type', ''),
                        purse=race_info.get('purse', 0),
                        conditions=race_info.get('race_restriction_description', '')
                    )
                    db.add(race)
                    races_synced += 1
            
            debug_info.extend(track_debug)
            total_races_synced += races_synced
        
        db.commit()
        return {
            "status": f"Manual sync completed - {total_races_synced} races synced across all tracks",
            "debug": debug_info,
            "total_api_races": total_races_synced
        }
        
    except Exception as e:
        import traceback
        return {"status": f"Manual sync failed: {str(e)}", "error": traceback.format_exc()}


@app.get("/api/debug/races")
async def debug_races(db: Session = Depends(get_db)):
    """Debug - show all races in database"""
    today = date.today()
    
    all_races = db.query(Race).all()
    today_races = db.query(Race).filter(Race.race_date == today).all()
    
    return {
        "today": today.strftime('%Y-%m-%d'),
        "total_races_in_db": len(all_races),
        "races_today": len(today_races),
        "today_races_detail": [
            {
                "id": race.id,
                "api_id": race.api_id,
                "track_id": race.track_id,
                "race_number": race.race_number,
                "race_date": race.race_date.strftime('%Y-%m-%d'),
                "race_time": race.race_time.strftime('%H:%M:%S'),
                "distance": race.distance,
                "surface": race.surface,
                "race_type": race.race_type,
                "purse": race.purse
            } for race in today_races
        ],
        "all_races_detail": [
            {
                "id": race.id,
                "api_id": race.api_id,
                "track_id": race.track_id,
                "race_number": race.race_number,
                "race_date": race.race_date.strftime('%Y-%m-%d') if race.race_date else None,
                "track_name": race.track.name if race.track else "Unknown"
            } for race in all_races[-10:]  # Last 10 races
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)