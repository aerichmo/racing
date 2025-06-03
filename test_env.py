#!/usr/bin/env python3
import os

print("=== Environment Variables Test ===")
print(f"DATABASE_URL: {'Set' if os.getenv('DATABASE_URL') else 'Not set'}")
print(f"RACING_API_USERNAME: {'Set' if os.getenv('RACING_API_USERNAME') else 'Not set'}")
print(f"RACING_API_PASSWORD: {'Set' if os.getenv('RACING_API_PASSWORD') else 'Not set'}")
print(f"RACING_API_BASE_URL: {'Set' if os.getenv('RACING_API_BASE_URL') else 'Not set'}")
print(f"PORT: {os.getenv('PORT', 'Not set')}")
print("================================")