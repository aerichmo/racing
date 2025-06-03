#!/usr/bin/env python3
"""
Script to add the missing 'name' column to the tracks table.
Run this on the server to fix the database schema.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv(override=False)
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=False)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        # Check if the column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tracks' AND column_name = 'name'
        """))
        
        if result.rowcount > 0:
            print("Column 'name' already exists in tracks table")
        else:
            # Add the column
            conn.execute(text("ALTER TABLE tracks ADD COLUMN name VARCHAR"))
            conn.execute(text("CREATE UNIQUE INDEX ix_tracks_name ON tracks(name)"))
            conn.commit()
            print("Successfully added 'name' column to tracks table")
            
            # Update existing records if needed
            result = conn.execute(text("SELECT id, code FROM tracks WHERE name IS NULL"))
            for row in result:
                track_id, code = row
                # Map code to name
                name_map = {
                    "RP": "Remington Park",
                    "FM": "Fair Meadows"
                }
                name = name_map.get(code, f"Track {code}")
                conn.execute(text("UPDATE tracks SET name = :name WHERE id = :id"), 
                           {"name": name, "id": track_id})
            conn.commit()
            print("Updated existing track records with names")
            
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

print("Database update completed successfully!")