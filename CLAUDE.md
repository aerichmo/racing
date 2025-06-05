# Racing Platform API Documentation

## Racing API Integration

The platform integrates with TheRacingAPI.com using three main endpoints:

### 1. List Meets
**URL**: `https://api.theracingapi.com/v1/north-america/meets`
**Purpose**: Get available racing meets by date
**Response**: List of meet objects

**Sample Response**:
```json
{
  "country": "USA",
  "date": "2025-06-11",
  "meet_id": "FMT_1749614400000",
  "track_id": "FMT",
  "track_name": "Fair Meadows Tulsa"
}
```

### 2. Meet Entries
**URL**: `https://api.theracingapi.com/v1/north-america/meets/{meet_id}/entries`
**Purpose**: Get all race entries for a specific meet
**Response**: Dictionary with meet info and nested races/runners

**Key Response Structure**:
```json
{
  "meet_id": "FMT_1749614400000",
  "track_id": "FMT", 
  "track_name": "Fair Meadows Tulsa",
  "races": [
    {
      "race_key": {"race_number": "1"},
      "post_time": "7:00 PM",
      "distance_description": "4 Furlongs",
      "surface_description": "Dirt",
      "race_type_description": "CLAIMING",
      "purse": 7700,
      "runners": [
        {
          "horse_name": "Smackzilla",
          "registration_number": "20020926",
          "program_number": "1",
          "weight": "125",
          "morning_line_odds": "",
          "jockey": {
            "id": "jky_na_362916",
            "first_name_initial": "T",
            "last_name": "Cunningham"
          },
          "trainer": {
            "id": "trn_na_8771850", 
            "first_name": "Eusebio",
            "last_name": "Rufino"
          }
        }
      ]
    }
  ]
}
```

### 3. Meet Results
**URL**: `https://api.theracingapi.com/v1/north-america/meets/{meet_id}/results`
**Purpose**: Get race results for finished races
**Response**: List of result objects (structure TBD when races finish)

## Important Field Mappings

### Track Identification
- **Fair Meadows**: 
  - Internal Code: `FM` 
  - API Track ID: `FMT`
  - Full Name: "Fair Meadows Tulsa"
- **Remington Park**: 
  - Internal Code: `RP`
  - API Track ID: `RP` 
  - Full Name: "Remington Park"

### Data Mapping
- `program_number` → post position
- `registration_number` → unique horse identifier
- `morning_line_odds` → often empty string, default to 5.0
- `weight` → string, convert to integer
- `jockey.id` → unique jockey identifier
- `trainer.id` → unique trainer identifier

## API Client Implementation

The `RacingAPIClient` class in `src/racing_api.py` handles:
- Authentication with Basic Auth
- Track code mapping (FM → FMT)
- Response transformation to legacy format
- Error handling for missing data

## Current Status
- ✅ API integration working correctly
- ✅ Fair Meadows data pulls from real API
- ✅ Complete schema documented in `api_schema_documentation.txt`
- ✅ Races scheduled for June 11, 2025 (not current date)

## Development Commands
- `python test_api_fixed.py` - Test API integration
- `python extract_api_schema.py` - Document API responses
- `curl -X POST /api/sync/initial` - Trigger data sync