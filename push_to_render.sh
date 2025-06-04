#!/bin/bash

echo "=== Pushing to Render ==="

# Check git status
echo "Checking git status..."
git status

# Add all changes
echo -e "\nAdding all changes..."
git add -A

# Commit changes
echo -e "\nCommitting changes..."
git commit -m "Debug Fair Meadows data issue - API investigation"

# Check remote
echo -e "\nChecking git remote..."
git remote -v

# Push to main branch (Render usually deploys from main)
echo -e "\nPushing to origin main..."
git push origin main

echo -e "\n=== Push complete ==="
echo "Check Render dashboard for deployment status"