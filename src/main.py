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

from database import get_db, Base, get_engine, Track, Race
from scheduler import RaceScheduler
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



@app.post("/api/sync/manual")
async def trigger_manual_sync(db: Session = Depends(get_db)):
    """Manual sync - simplified direct approach"""
    try:
        from data_sync import DataSync
        from racing_api import RacingAPIClient
        
        api_client = RacingAPIClient()
        today = date.today()
        
        # Get Fair Meadows track
        track = db.query(Track).filter(Track.name == "Fair Meadows").first()
        if not track:
            return {"status": "Fair Meadows track not found in database"}
        
        # Get races directly from API
        races_data = await api_client.get_races_by_date("FM", today)
        
        races_synced = 0
        debug_info = [f"API response keys: {list(races_data.keys()) if races_data else 'None'}"]
        debug_info.append(f"Races in response: {len(races_data.get('races', []))} if races_data else 0")
        
        if races_data and 'races' in races_data:
            debug_info.append(f"First race sample: {races_data['races'][0] if races_data['races'] else 'No races'}")
        else:
            debug_info.append(f"Full API response: {races_data}")
        
        for i, race_info in enumerate(races_data.get('races', [])):
            # Extract race key and number
            race_key = race_info.get('race_key', '')
            debug_info.append(f"Race {i}: race_key={race_key}, type={type(race_key)}")
            
            if not race_key:
                continue
                
            # Handle race_key that might be a dict or other type
            if isinstance(race_key, dict):
                race_number = int(race_key.get('race_number', i + 1))
                race_key = f"R{race_number}"
            elif isinstance(race_key, str) and race_key.startswith('R'):
                race_number = int(race_key.replace('R', ''))
            else:
                race_number = i + 1
                race_key = f"R{race_number}"
            
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
                    conditions=race_info.get('race_restriction_description', ''),
                    track_name=track.name
                )
                db.add(race)
                races_synced += 1
        
        db.commit()
        return {
            "status": f"Manual sync completed - {races_synced} races synced for Fair Meadows",
            "debug": debug_info,
            "total_api_races": len(races_data.get('races', []))
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