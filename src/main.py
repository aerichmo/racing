from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
import asyncio
import re
from typing import List, Dict, Set
from pathlib import Path
from contextlib import asynccontextmanager
import json

from database import get_db, Base, get_engine, Track, Race, Bet, BetResult, DailyROI, RaceEntry, RaceResult, Horse, Jockey, Trainer, OddsHistory
from betting_engine import BettingEngine
import os

# Get the base directory (parent of src)
BASE_DIR = Path(__file__).resolve().parent.parent

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, track_id: int):
        await websocket.accept()
        if track_id not in self.active_connections:
            self.active_connections[track_id] = set()
        self.active_connections[track_id].add(websocket)
        
    def disconnect(self, websocket: WebSocket, track_id: int):
        if track_id in self.active_connections:
            self.active_connections[track_id].discard(websocket)
            if not self.active_connections[track_id]:
                del self.active_connections[track_id]
                
    async def broadcast_odds(self, track_id: int, data: dict):
        if track_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[track_id]:
                try:
                    await connection.send_json(data)
                except:
                    disconnected.add(connection)
            # Clean up disconnected clients
            for conn in disconnected:
                self.disconnect(conn, track_id)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Create database tables after environment variables are loaded
    Base.metadata.create_all(bind=get_engine())
    
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

@app.get("/admin/odds", response_class=HTMLResponse)
async def admin_odds_page():
    template_path = BASE_DIR / "templates" / "admin_odds.html"
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


@app.post("/api/sync")
async def trigger_sync(db: Session = Depends(get_db)):
    """Comprehensive manual sync with detailed debugging"""
    try:
        from racing_api import RacingAPIClient
        import traceback
        
        api_client = RacingAPIClient()
        today = date.today()
        
        # Get both tracks
        tracks = [
            {"name": "Remington Park", "code": "RP"},
            {"name": "Fair Meadows", "code": "FM"}
        ]
        
        total_races_synced = 0
        debug_info = [f"Starting sync for date: {today}"]
        
        for track_data in tracks:
            track = db.query(Track).filter(Track.name == track_data["name"]).first()
            if not track:
                debug_info.append(f"❌ {track_data['name']} track not found in database")
                continue
            
            debug_info.append(f"🏁 Processing {track_data['name']} (code: {track_data['code']} -> API)")
            
            try:
                # Get races directly from API
                races_data = await api_client.get_races_by_date(track_data["code"], today)
                
                if races_data is None:
                    debug_info.append(f"❌ {track_data['name']}: API returned None")
                    continue
                
                debug_info.append(f"📡 {track_data['name']} API response keys: {list(races_data.keys())}")
                
                # Check for debug info in response
                if 'debug' in races_data:
                    debug_info.append(f"🔍 {track_data['name']} API debug: {races_data['debug']}")
                
                # Handle both 'entries' and 'races' response formats
                entries = races_data.get('entries', [])
                races = races_data.get('races', [])
                
                if races and not entries:
                    # 'races' format - extract entries from each race
                    debug_info.append(f"📋 {track_data['name']}: {len(races)} races returned (races format)")
                    
                    races_by_number = {}
                    race_keys_found = []
                    
                    for i, race in enumerate(races):
                        # Extract race number from race_key (could be string or dict)
                        race_key = race.get('race_key', '')
                        race_num = None
                        
                        if race_key:
                            # Handle if race_key is a dict (extract key or relevant field)
                            if isinstance(race_key, dict):
                                # Try common fields that might contain the race number
                                race_key_str = (str(race_key.get('key', '')) or 
                                              str(race_key.get('id', '')) or 
                                              str(race_key.get('number', '')) or
                                              str(race_key))
                            else:
                                race_key_str = str(race_key)
                            
                            # Extract number from race_key string (e.g., "R1" -> 1)
                            match = re.search(r'(\d+)', race_key_str)
                            if match:
                                race_num = int(match.group(1))
                        
                        # Fallback to other fields if race_key doesn't work
                        if not race_num:
                            race_num = (race.get('race_number') or 
                                       race.get('raceNumber') or 
                                       race.get('number') or
                                       i + 1)  # fallback to index + 1
                        
                        # Show race_key structure in debug
                        if isinstance(race_key, dict):
                            race_key_display = f"dict:{list(race_key.keys())}"
                        else:
                            race_key_display = str(race_key)
                        race_keys_found.append(f"{race_key_display}→{race_num}")
                        
                        if race_num:
                            races_by_number[race_num] = race
                    
                    debug_info.append(f"🔑 Race keys: {', '.join(race_keys_found[:5])}{'...' if len(race_keys_found) > 5 else ''}")
                else:
                    # 'entries' format - group by race number
                    debug_info.append(f"📋 {track_data['name']}: {len(entries)} entries returned (entries format)")
                    if not entries:
                        debug_info.append(f"⚠️ {track_data['name']}: No entries found")
                        continue
                    
                    races_by_number = {}
                    for entry in entries:
                        race_num = entry.get('race_number', 0)
                        if race_num and race_num not in races_by_number:
                            races_by_number[race_num] = entry
                
                debug_info.append(f"🏇 {track_data['name']}: Found {len(races_by_number)} unique races: {list(races_by_number.keys())}")
                
                races_synced = 0
                for race_number, race_info in races_by_number.items():
                    race_key = f"R{race_number}"
                    
                    # Check if already exists
                    existing = db.query(Race).filter(
                        Race.api_id == race_key,
                        Race.track_id == track.id,
                        Race.race_date == today
                    ).first()
                    
                    if existing:
                        debug_info.append(f"⏭️ {track_data['name']} Race {race_number}: Already exists")
                        continue
                    
                    # Debug: show all available fields in race_info
                    debug_info.append(f"📋 Race {race_number} available fields: {list(race_info.keys())}")
                    
                    # Parse post time - try multiple possible field names
                    post_time_str = (race_info.get('post_time', '') or 
                                   race_info.get('postTime', '') or 
                                   race_info.get('race_time', '') or
                                   race_info.get('scheduled_start', '') or
                                   race_info.get('start_time', ''))
                    
                    debug_info.append(f"🕒 Race {race_number} post_time from API: '{post_time_str}'")
                    
                    if post_time_str:
                        try:
                            race_time = datetime.fromisoformat(post_time_str.replace('Z', '+00:00'))
                            debug_info.append(f"✅ Parsed race time: {race_time.strftime('%I:%M %p')}")
                        except Exception as parse_error:
                            race_time = datetime.now()
                            debug_info.append(f"❌ Failed to parse post_time '{post_time_str}': {parse_error}")
                    else:
                        race_time = datetime.now()
                        debug_info.append(f"⚠️ No post_time provided, using current time: {race_time.strftime('%I:%M %p')}")
                    
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
                    debug_info.append(f"✅ {track_data['name']} Race {race_number}: Added to database")
                
                total_races_synced += races_synced
                debug_info.append(f"🎯 {track_data['name']}: Synced {races_synced} new races")
                
            except Exception as track_error:
                debug_info.append(f"❌ {track_data['name']} error: {str(track_error)}")
                debug_info.append(f"🔍 {track_data['name']} traceback: {traceback.format_exc()}")
        
        db.commit()
        
        # Check for most recent racing day if no races today
        last_race_info = {}
        if total_races_synced == 0:
            # Find the most recent race date for each track
            for track_data in tracks:
                track = db.query(Track).filter(Track.name == track_data["name"]).first()
                if track:
                    last_race = db.query(Race).filter(
                        Race.track_id == track.id
                    ).order_by(Race.race_date.desc()).first()
                    
                    if last_race:
                        last_race_info[track_data["name"]] = {
                            "last_race_date": last_race.race_date.strftime("%Y-%m-%d"),
                            "races_that_day": db.query(Race).filter(
                                Race.track_id == track.id,
                                Race.race_date == last_race.race_date
                            ).count()
                        }
        
        # Final status with better explanation
        status_msg = f"Sync completed: {total_races_synced} races synced"
        if total_races_synced == 0:
            status_msg += " ⚠️ No races scheduled for today"
            if last_race_info:
                debug_info.append("📅 Last racing days:")
                for track_name, info in last_race_info.items():
                    debug_info.append(f"   {track_name}: {info['last_race_date']} ({info['races_that_day']} races)")
            
            debug_info.append("💡 This is normal - not all tracks race every day")
        
        return {
            "status": status_msg,
            "races_synced": total_races_synced,
            "debug": debug_info,
            "date": today.strftime("%Y-%m-%d"),
            "last_race_info": last_race_info if total_races_synced == 0 else {}
        }
        
    except Exception as e:
        import traceback
        return {
            "status": f"Sync failed: {str(e)}",
            "error": traceback.format_exc(),
            "debug": debug_info if 'debug_info' in locals() else ["Error occurred before debug initialization"]
        }


@app.post("/api/sync-entries")
async def sync_race_entries(db: Session = Depends(get_db)):
    """Sync entries (horses, jockeys, trainers) for existing races and generate betting recommendations"""
    try:
        from data_sync import DataSync
        from betting_engine import BettingEngine
        import traceback
        
        debug_info = []
        sync = DataSync()
        
        # Add timeout and chunking
        today = date.today()
        races = db.query(Race).filter(Race.race_date == today).all()
        
        debug_info.append(f"Found {len(races)} races to sync")
        
        synced_count = 0
        
        # Process races in chunks to avoid timeout
        for i, race in enumerate(races[:5]):  # Limit to first 5 races
            try:
                debug_info.append(f"Processing race {race.race_number}...")
                
                # Sync entries for this race
                entries_data = await sync.api_client.get_race_entries(
                    'FM' if race.track_id == 2 else 'RP', 
                    today, 
                    race.race_number
                )
                
                await sync._sync_entries(db, race.id, entries_data)
                db.commit()
                
                # Count entries for this race
                race_entries = db.query(RaceEntry).filter(RaceEntry.race_id == race.id).count()
                debug_info.append(f"Race {race.race_number}: {race_entries} entries")
                synced_count += race_entries
                
            except Exception as race_error:
                debug_info.append(f"Race {race.race_number} failed: {str(race_error)}")
                continue
        
        # Generate betting recommendations for races with entries
        if synced_count > 0:
            debug_info.append("Generating betting recommendations...")
            engine = BettingEngine(db)
            
            races_with_entries = db.query(Race).join(RaceEntry).filter(
                Race.race_date == today
            ).distinct().all()
            
            generated_bets = 0
            for race in races_with_entries:
                try:
                    # Generate recommendations using the betting engine
                    recommendations = await engine.analyze_race(race)
                    
                    for rec in recommendations:
                        # Check if bet already exists
                        existing_bet = db.query(Bet).filter(
                            Bet.race_id == race.id,
                            Bet.entry_id == rec['entry_id']
                        ).first()
                        
                        if not existing_bet:
                            bet = Bet(
                                race_id=race.id,
                                entry_id=rec['entry_id'],
                                bet_type=rec.get('bet_type', 'WIN'),
                                amount=rec['bet_amount'],
                                odds=rec['current_odds'],
                                confidence=rec['confidence'],
                                expected_value=rec['expected_value']
                            )
                            db.add(bet)
                            generated_bets += 1
                            
                except Exception as bet_error:
                    debug_info.append(f"Bet generation failed for race {race.race_number}: {str(bet_error)}")
                    continue
            
            db.commit()
            debug_info.append(f"Generated {generated_bets} betting recommendations")
        
        # Also check for results on completed races
        results_processed = 0
        from datetime import timedelta
        
        # Get races from today that might have finished (post time was > 5 minutes ago)
        now = datetime.now()
        five_minutes_ago = now - timedelta(minutes=5)
        
        completed_races = db.query(Race).filter(
            Race.race_date == today,
            Race.race_time <= five_minutes_ago
        ).all()
        
        debug_info.append(f"Checking {len(completed_races)} potentially completed races for results")
        
        for race in completed_races:
            try:
                # Check if we already have results for this race
                existing_results = db.query(RaceResult).join(RaceEntry).filter(
                    RaceEntry.race_id == race.id
                ).first()
                
                if not existing_results:
                    # Try to fetch results
                    from racing_api import RacingAPIClient
                    api_client = RacingAPIClient()
                    track_code = 'RP' if race.track_id == 1 else 'FM'
                    
                    results_data = await api_client.get_race_results(track_code, race.race_date, race.race_number)
                    
                    if results_data and results_data.get('results'):
                        # Process results
                        for result in results_data['results']:
                            horse_name = result.get('horse_name', '')
                            entry = db.query(RaceEntry).join(Horse).filter(
                                RaceEntry.race_id == race.id,
                                Horse.name == horse_name
                            ).first()
                            
                            if entry:
                                race_result = RaceResult(
                                    entry_id=entry.id,
                                    finish_position=result.get('finish_position', 0),
                                    win_odds=result.get('win_odds', 0),
                                    place_odds=result.get('place_odds', 0),
                                    show_odds=result.get('show_odds', 0),
                                    margin=result.get('margin', 0),
                                    time=result.get('time', 0)
                                )
                                db.add(race_result)
                        
                        # Calculate bet results for this race
                        bets = db.query(Bet).filter(Bet.race_id == race.id).all()
                        for bet in bets:
                            existing_bet_result = db.query(BetResult).filter(
                                BetResult.bet_id == bet.id
                            ).first()
                            
                            if not existing_bet_result and bet.entry.result:
                                won = bet.entry.result.finish_position == 1  # WIN bets only
                                payout = bet.amount * (bet.entry.result.win_odds + 1) if won else 0.0
                                
                                bet_result = BetResult(
                                    bet_id=bet.id,
                                    won=won,
                                    payout=payout
                                )
                                db.add(bet_result)
                        
                        db.commit()
                        results_processed += 1
                        debug_info.append(f"✅ Results processed for race {race.race_number}")
                    else:
                        debug_info.append(f"⏳ No results yet for race {race.race_number}")
            except Exception as result_error:
                debug_info.append(f"❌ Results fetch failed for race {race.race_number}: {str(result_error)}")
                continue
        
        debug_info.append(f"Processed results for {results_processed} races")
        
        # Count total entries
        total_entries = db.query(RaceEntry).join(Race).filter(
            Race.race_date == today
        ).count()
        
        return {
            "status": "Entry sync completed",
            "entries_count": total_entries,
            "entries_synced": synced_count,
            "results_processed": results_processed,
            "debug": debug_info,
            "message": f"Synced {synced_count} new entries, processed {results_processed} race results, {total_entries} total entries for today"
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "Entry sync failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "debug": debug_info if 'debug_info' in locals() else []
        }







@app.post("/api/results/{race_id}")
async def log_race_results(race_id: int, db: Session = Depends(get_db)):
    """Fetch and log race results, calculate performance metrics"""
    try:
        from racing_api import RacingAPIClient
        
        race = db.query(Race).filter(Race.id == race_id).first()
        if not race:
            raise HTTPException(status_code=404, detail="Race not found")
        
        # Get track code
        track_code = 'RP' if race.track_id == 1 else 'FM'
        
        # Fetch results from API
        api_client = RacingAPIClient()
        results_data = await api_client.get_race_results(track_code, race.race_date, race.race_number)
        
        if not results_data:
            return {"status": "No results available yet", "race_id": race_id}
        
        # Process results
        results_logged = 0
        for result in results_data.get('results', []):
            # Find the entry
            horse_name = result.get('horse_name', '')
            entry = db.query(RaceEntry).join(Horse).filter(
                RaceEntry.race_id == race_id,
                Horse.name == horse_name
            ).first()
            
            if entry:
                # Check if result already exists
                existing_result = db.query(RaceResult).filter(
                    RaceResult.entry_id == entry.id
                ).first()
                
                if not existing_result:
                    race_result = RaceResult(
                        entry_id=entry.id,
                        finish_position=result.get('finish_position', 0),
                        win_odds=result.get('win_odds', 0),
                        place_odds=result.get('place_odds', 0),
                        show_odds=result.get('show_odds', 0),
                        margin=result.get('margin', 0),
                        time=result.get('time', 0)
                    )
                    db.add(race_result)
                    results_logged += 1
        
        db.commit()
        
        # Calculate bet results
        bets = db.query(Bet).filter(Bet.race_id == race_id).all()
        bet_results_calculated = 0
        
        for bet in bets:
            # Check if bet result already exists
            existing_bet_result = db.query(BetResult).filter(
                BetResult.bet_id == bet.id
            ).first()
            
            if not existing_bet_result and bet.entry.result:
                # Calculate if bet won
                won = False
                payout = 0.0
                
                if bet.bet_type == 'WIN':
                    won = bet.entry.result.finish_position == 1
                    if won:
                        payout = bet.amount * (bet.entry.result.win_odds + 1)
                elif bet.bet_type == 'PLACE':
                    won = bet.entry.result.finish_position <= 2
                    if won:
                        payout = bet.amount * (bet.entry.result.place_odds + 1)
                elif bet.bet_type == 'SHOW':
                    won = bet.entry.result.finish_position <= 3
                    if won:
                        payout = bet.amount * (bet.entry.result.show_odds + 1)
                
                bet_result = BetResult(
                    bet_id=bet.id,
                    won=won,
                    payout=payout
                )
                db.add(bet_result)
                bet_results_calculated += 1
        
        db.commit()
        
        # Update daily ROI
        today = race.race_date
        daily_roi = db.query(DailyROI).filter(
            DailyROI.track_id == race.track_id,
            DailyROI.date == today
        ).first()
        
        if not daily_roi:
            daily_roi = DailyROI(
                track_id=race.track_id,
                date=today,
                total_wagered=0,
                total_returned=0,
                roi_percentage=0
            )
            db.add(daily_roi)
        
        # Recalculate daily totals
        daily_bets = db.query(Bet).join(Race).filter(
            Race.track_id == race.track_id,
            Race.race_date == today
        ).all()
        
        total_wagered = sum(bet.amount for bet in daily_bets)
        total_returned = sum(
            bet.result.payout 
            for bet in daily_bets 
            if hasattr(bet, 'result') and bet.result
        )
        
        daily_roi.total_wagered = total_wagered
        daily_roi.total_returned = total_returned
        daily_roi.roi_percentage = ((total_returned - total_wagered) / total_wagered * 100) if total_wagered > 0 else 0
        
        db.commit()
        
        return {
            "status": "Results logged successfully",
            "race_id": race_id,
            "results_logged": results_logged,
            "bet_results_calculated": bet_results_calculated,
            "performance": {
                "total_wagered": total_wagered,
                "total_returned": total_returned,
                "roi": daily_roi.roi_percentage
            }
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "Failed to log results",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/api/performance/{track_id}")
async def get_performance_metrics(track_id: int, days: int = 30, db: Session = Depends(get_db)):
    """Get performance metrics for a track"""
    from datetime import timedelta
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    # Get daily ROI data
    daily_rois = db.query(DailyROI).filter(
        DailyROI.track_id == track_id,
        DailyROI.date >= start_date,
        DailyROI.date <= end_date
    ).order_by(DailyROI.date.desc()).all()
    
    # Get win rate by confidence level
    confidence_stats = []
    for conf_level, conf_name in [(0.8, "High"), (0.6, "Medium"), (0.0, "Low")]:
        next_level = 1.0 if conf_level == 0.8 else (0.8 if conf_level == 0.6 else 0.6)
        
        bets = db.query(Bet).join(Race).filter(
            Race.track_id == track_id,
            Race.race_date >= start_date,
            Bet.confidence >= conf_level,
            Bet.confidence < next_level
        ).all()
        
        total_bets = len(bets)
        winning_bets = sum(1 for bet in bets if hasattr(bet, 'result') and bet.result and bet.result.won)
        
        confidence_stats.append({
            "level": conf_name,
            "total_bets": total_bets,
            "winning_bets": winning_bets,
            "win_rate": (winning_bets / total_bets * 100) if total_bets > 0 else 0
        })
    
    # Calculate overall stats
    all_bets = db.query(Bet).join(Race).filter(
        Race.track_id == track_id,
        Race.race_date >= start_date
    ).all()
    
    total_wagered = sum(bet.amount for bet in all_bets)
    total_returned = sum(
        bet.result.payout 
        for bet in all_bets 
        if hasattr(bet, 'result') and bet.result
    )
    
    return {
        "track_id": track_id,
        "period_days": days,
        "overall_stats": {
            "total_races": len(set(bet.race_id for bet in all_bets)),
            "total_bets": len(all_bets),
            "total_wagered": round(total_wagered, 2),
            "total_returned": round(total_returned, 2),
            "net_profit": round(total_returned - total_wagered, 2),
            "roi_percentage": round(((total_returned - total_wagered) / total_wagered * 100) if total_wagered > 0 else 0, 2)
        },
        "confidence_performance": confidence_stats,
        "daily_roi": [
            {
                "date": roi.date.strftime("%Y-%m-%d"),
                "wagered": round(roi.total_wagered, 2),
                "returned": round(roi.total_returned, 2),
                "roi": round(roi.roi_percentage, 2)
            } for roi in daily_rois
        ]
    }


# WebSocket endpoint for live odds streaming
@app.websocket("/ws/odds/{track_id}")
async def websocket_odds(websocket: WebSocket, track_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket, track_id)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # Could handle client messages here if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket, track_id)


# Manual odds update endpoint
@app.post("/api/odds/manual")
async def update_manual_odds(
    race_id: int,
    entry_id: int,
    odds: float,
    db: Session = Depends(get_db)
):
    """Manually update odds for a specific entry and broadcast via WebSocket"""
    try:
        # Update the odds in the database
        entry = db.query(RaceEntry).filter(
            RaceEntry.id == entry_id,
            RaceEntry.race_id == race_id
        ).first()
        
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
            
        # Save old odds for history
        old_odds = entry.current_odds
        
        # Update current odds
        entry.current_odds = odds
        
        # Add to odds history
        odds_history = OddsHistory(
            entry_id=entry_id,
            odds=odds,
            source='manual'
        )
        db.add(odds_history)
        
        db.commit()
        
        # Get track_id for broadcasting
        race = db.query(Race).filter(Race.id == race_id).first()
        if race:
            # Broadcast the update via WebSocket
            await manager.broadcast_odds(race.track_id, {
                "type": "odds_update",
                "race_id": race_id,
                "entry_id": entry_id,
                "horse_name": entry.horse.name,
                "new_odds": odds,
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "status": "success",
            "race_id": race_id,
            "entry_id": entry_id,
            "new_odds": odds
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Get live odds endpoint
@app.get("/api/odds/live/{track_id}")
async def get_live_odds(track_id: int, db: Session = Depends(get_db)):
    """Get current live odds for all races at a track today"""
    today = date.today()
    
    races = db.query(Race).filter(
        Race.track_id == track_id,
        Race.race_date == today
    ).order_by(Race.race_time).all()
    
    live_odds = []
    for race in races:
        entries = db.query(RaceEntry).filter(
            RaceEntry.race_id == race.id
        ).order_by(RaceEntry.post_position).all()
        
        race_odds = {
            "race_id": race.id,
            "race_number": race.race_number,
            "race_time": race.race_time.strftime("%I:%M %p"),
            "entries": [
                {
                    "entry_id": entry.id,
                    "post_position": entry.post_position,
                    "horse_name": entry.horse.name,
                    "jockey": entry.jockey.name if entry.jockey else "Unknown",
                    "current_odds": entry.current_odds,
                    "morning_line": entry.morning_line_odds
                }
                for entry in entries
            ]
        }
        live_odds.append(race_odds)
        
    return {"track_id": track_id, "races": live_odds}


# Get optimal betting recommendations
@app.get("/api/betting/optimal/{track_id}")
async def get_optimal_bets(track_id: int, bankroll: float = 1000.0, db: Session = Depends(get_db)):
    """Get optimal Win/Place/Show betting recommendations based on current odds"""
    try:
        from simple_optimal_model import SimpleOptimalBettingModel
        
        model = SimpleOptimalBettingModel(db, bankroll)
        today = date.today()
        
        races = db.query(Race).filter(
            Race.track_id == track_id,
            Race.race_date == today
        ).order_by(Race.race_time).all()
        
        all_recommendations = []
        
        for race in races:
            recommendations = model.analyze_race(race)
            if recommendations:
                all_recommendations.append({
                    "race_id": race.id,
                    "race_number": race.race_number,
                    "race_time": race.race_time.strftime("%I:%M %p"),
                    "recommendations": recommendations
                })
                
        return {
            "track_id": track_id,
            "bankroll": bankroll,
            "recommendations": all_recommendations,
            "total_races": len(races),
            "races_with_bets": len(all_recommendations)
        }
        
    except ImportError:
        # If model not yet implemented, return placeholder
        return {
            "track_id": track_id,
            "bankroll": bankroll,
            "recommendations": [],
            "message": "Optimal betting model not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)