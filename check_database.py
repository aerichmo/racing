#!/usr/bin/env python3
import psycopg2
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("Connected to database successfully\n")
    
    # Check tracks table
    cur.execute("SELECT * FROM tracks WHERE code = 'FM'")
    track = cur.fetchone()
    if track:
        print(f"Fair Meadows found in tracks table: {track}")
        track_id = track[0]
    else:
        print("Fair Meadows NOT found in tracks table!")
        cur.execute("SELECT * FROM tracks")
        all_tracks = cur.fetchall()
        print(f"\nAll tracks in database: {all_tracks}")
        track_id = None
    
    # Check recent races
    if track_id:
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        cur.execute("""
            SELECT COUNT(*) as race_count, MIN(race_date), MAX(race_date) 
            FROM races 
            WHERE track_id = %s AND race_date >= %s
        """, (track_id, week_ago))
        
        race_stats = cur.fetchone()
        print(f"\nRaces in last 7 days: {race_stats[0]}")
        if race_stats[0] > 0:
            print(f"Date range: {race_stats[1]} to {race_stats[2]}")
        
        # Check today's races specifically
        cur.execute("""
            SELECT id, race_number, race_date, post_time, distance, surface, race_type 
            FROM races 
            WHERE track_id = %s AND race_date = %s
            ORDER BY race_number
        """, (track_id, today))
        
        today_races = cur.fetchall()
        print(f"\nRaces today ({today}): {len(today_races)}")
        for race in today_races:
            print(f"  Race {race[1]}: {race}")
            
        # Check if there are any entries
        if today_races:
            race_id = today_races[0][0]
            cur.execute("SELECT COUNT(*) FROM race_entries WHERE race_id = %s", (race_id,))
            entry_count = cur.fetchone()[0]
            print(f"\nEntries in first race: {entry_count}")
    
    # Check last sync time
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'sync_log'
    """)
    
    if cur.fetchone():
        cur.execute("""
            SELECT sync_type, sync_date, status, details 
            FROM sync_log 
            WHERE track_code = 'FM' 
            ORDER BY sync_date DESC 
            LIMIT 5
        """)
        sync_logs = cur.fetchall()
        print(f"\nRecent sync logs for Fair Meadows:")
        for log in sync_logs:
            print(f"  {log}")
    else:
        print("\nNo sync_log table found")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Database error: {e}")