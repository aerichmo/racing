#!/usr/bin/env python3
import os
import sys
from sqlalchemy import text, inspect

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql://mob1e_user:dU3nupu3FgdqClieo5JZWoZ2eL1KSMZB@dpg-d0lk5oogjchc73f5ieqg-a.oregon-postgres.render.com/mob1e'

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import get_engine, Base

def fix_database():
    engine = get_engine()
    
    print("Fixing database schema...")
    
    with engine.connect() as conn:
        # Drop all tables and recreate
        print("Dropping existing tables...")
        conn.execute(text("DROP TABLE IF EXISTS daily_roi CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS bet_results CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS bets CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS race_results CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS race_entries CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS historical_performances CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS races CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS horses CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS jockeys CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS trainers CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS tracks CASCADE"))
        conn.commit()
        
    print("Creating tables with correct schema...")
    Base.metadata.create_all(bind=engine)
    
    print("Database schema fixed!")

if __name__ == "__main__":
    fix_database()