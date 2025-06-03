#!/bin/sh

# Print environment variables for debugging (remove in production)
echo "Environment variables:"
env | grep -E "DATABASE_URL|RACING_API|PORT" | sed 's/=.*/=***/'

# Change to src directory and run the application
cd src
exec python main.py