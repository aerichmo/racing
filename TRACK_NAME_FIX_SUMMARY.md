# Track Name Column Fix Summary

## Problem
The application is failing with the error:
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.UndefinedColumn) column "track_name" of relation "historical_performances" does not exist
```

## Root Cause
The `track_name` column was being referenced in two places:
1. The `HistoricalPerformance` model in `database.py`
2. The data sync code in `data_sync.py` when creating new `HistoricalPerformance` records

## Changes Made

### 1. Updated `database.py`
- Removed `track_name = Column(String)` from the `HistoricalPerformance` class (line 131)

### 2. Updated `data_sync.py`
- Removed `track_name=perf.get('track_name'),` from the `HistoricalPerformance` object creation (line 255)

### 3. Created Alembic Migration
- Created migration file: `/home/alecrichmo/racing/migrations/versions/94af63798d7e_remove_track_name_from_historical_.py`
- This migration drops the `track_name` column from the `historical_performances` table

### 4. Created Manual Fix Script
- Created script: `/home/alecrichmo/racing/fix_track_name_column.py`
- This script can be run manually to drop the column if the migration cannot be run

## Other References Found (No Changes Needed)
The following references to "track_name" were found but don't need changes as they're not database column references:
- `main.py`: Uses track_name in API responses (getting it from track.name relationship)
- `scheduler.py`: Uses track_name in a loop variable for track names
- `data_sync.py`: Uses track_name as a loop variable when iterating over track_codes dictionary

## How to Apply the Fix

### Option 1: Run the Alembic Migration
```bash
cd /home/alecrichmo/racing
alembic upgrade head
```

### Option 2: Run the Manual Fix Script
```bash
cd /home/alecrichmo/racing
python fix_track_name_column.py
```

### Option 3: Manual SQL Command
If both options above fail, you can run this SQL directly:
```sql
ALTER TABLE historical_performances DROP COLUMN IF EXISTS track_name;
```

## After Applying the Fix
1. Restart the application to ensure it picks up the model changes
2. The error should be resolved

## Verification
To verify the fix worked, check that:
1. The application starts without the IntegrityError
2. Historical performance data can be synced without errors
3. The API endpoints work correctly