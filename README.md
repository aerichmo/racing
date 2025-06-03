# Horse Racing Betting Platform

A data-driven betting platform for horse racing that analyzes historical performance data to generate profitable betting recommendations.

## Features

- **Automated Data Syncing**: Pulls data from theracingapi at strategic times (8 AM, 1 hour before first race, 10 minutes before each race)
- **Smart Betting Engine**: Uses machine learning to analyze horse, jockey, and trainer performance
- **Track Support**: Currently supports Remington Park and Fair Meadows
- **Budget Management**: $100 daily budget per track with max $50 per race
- **ROI Tracking**: Real-time and historical ROI tracking
- **Web Interface**: Clean, responsive interface showing recommendations and results

## Deployment on Render

1. Connect your GitHub repository to Render
2. Select "New Web Service"
3. Choose Docker runtime
4. The `render.yaml` file contains all necessary configuration
5. Deploy!

## API Endpoints

- `GET /` - Main web interface
- `GET /api/tracks` - List supported tracks
- `GET /api/recommendations/{track_id}` - Get betting recommendations
- `GET /api/race-results/{race_id}` - Get race results
- `GET /api/roi/{track_id}` - Get ROI statistics
- `POST /api/sync/initial` - Manual trigger for initial sync
- `POST /api/sync/pre-race` - Manual trigger for pre-race sync

## Environment Variables

All environment variables are configured in the `render.yaml` file:
- `DATABASE_URL` - PostgreSQL connection string
- `RACING_API_USERNAME` - TheRacingAPI username
- `RACING_API_PASSWORD` - TheRacingAPI password
- `RACING_API_BASE_URL` - API base URL
- `PORT` - Application port (default 8000)

## Database Schema

The platform uses PostgreSQL with tables for:
- Tracks, Horses, Jockeys, Trainers
- Races and Race Entries
- Race Results
- Historical Performance Data
- Bets and Bet Results
- Daily ROI Tracking

## Betting Strategy

The platform uses a sophisticated analysis engine that considers:
- Horse performance history (recent form, distance/surface preferences)
- Jockey and trainer win rates
- Post position statistics
- Days since last race (freshness factor)
- Speed figures and beaten lengths

Bets are placed using a conservative Kelly Criterion approach (25% fraction) with expected value thresholds.