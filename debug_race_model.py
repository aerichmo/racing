#!/usr/bin/env python
"""Debug script to check Race model columns"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import Race, get_engine, Base
from sqlalchemy import inspect

# Get the Race model columns from SQLAlchemy
print("Columns defined in Race model:")
for column in Race.__table__.columns:
    print(f"  - {column.name}: {column.type}")

print("\nChecking if 'track_name' is in the model:")
print(f"  'track_name' in columns: {'track_name' in [c.name for c in Race.__table__.columns]}")

# Get the actual database schema
engine = get_engine()
inspector = inspect(engine)

print("\nColumns in the actual 'races' table in database:")
columns = inspector.get_columns('races')
for col in columns:
    print(f"  - {col['name']}: {col['type']}")

print("\nChecking if 'track_name' exists in database:")
db_columns = [col['name'] for col in columns]
print(f"  'track_name' in database: {'track_name' in db_columns}")

# Check if there's a mismatch
model_columns = set(c.name for c in Race.__table__.columns)
db_columns_set = set(db_columns)

print("\nColumns in model but not in database:")
for col in model_columns - db_columns_set:
    print(f"  - {col}")

print("\nColumns in database but not in model:")
for col in db_columns_set - model_columns:
    print(f"  - {col}")