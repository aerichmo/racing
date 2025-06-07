#!/usr/bin/env python3
"""
Script to remove track_name column from historical_performances table
and ensure the application can run without errors.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_database():
    """Remove track_name column from historical_performances table."""
    try:
        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("ERROR: DATABASE_URL not found in environment variables")
            return False
            
        # Create engine
        engine = create_engine(database_url)
        
        # Check if column exists and drop it
        with engine.connect() as conn:
            # Check if the column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'historical_performances' 
                AND column_name = 'track_name'
            """))
            
            if result.fetchone():
                print("Found track_name column in historical_performances table. Dropping it...")
                conn.execute(text("ALTER TABLE historical_performances DROP COLUMN track_name"))
                conn.commit()
                print("Successfully dropped track_name column from historical_performances table")
            else:
                print("track_name column not found in historical_performances table (already removed)")
                
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to fix database: {e}")
        return False

if __name__ == "__main__":
    print("Fixing database schema...")
    if fix_database():
        print("\nDatabase schema fixed successfully!")
        print("\nNext steps:")
        print("1. Restart the application to pick up the model changes")
        print("2. The error should be resolved")
    else:
        print("\nFailed to fix database schema")
        sys.exit(1)