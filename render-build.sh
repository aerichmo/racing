#!/usr/bin/env bash
# This script is for Render's native Python runtime, not Docker

# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# No need to do anything else as Render will handle running the app