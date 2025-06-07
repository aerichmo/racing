#!/usr/bin/env python
"""Temporarily add track_name column to races table"""

import os
import psycopg2
from urllib.parse import urlparse

# Parse DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("DATABASE_URL not set")
    exit(1)

# Parse the URL
result = urlparse(database_url)

# Connect to database
conn = psycopg2.connect(
    database=result.path[1:],
    user=result.username,
    password=result.password,
    host=result.hostname,
    port=result.port
)

cur = conn.cursor()

try:
    # Add the column temporarily
    cur.execute("ALTER TABLE races ADD COLUMN IF NOT EXISTS track_name VARCHAR")
    conn.commit()
    print("Successfully added track_name column to races table")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()