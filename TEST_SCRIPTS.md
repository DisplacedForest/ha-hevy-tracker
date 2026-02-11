# Test Scripts for Hevy Integration

This directory contains test scripts for validating the Hevy API integration features.

## Setup

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Add your Hevy API key to `.env`:**
   ```bash
   HEVY_API_KEY=your-api-key-here
   ```

3. **The `.env` file is gitignored** - your API key will not be committed.

## Available Test Scripts

### `test_corrected_implementation.py`
Tests the exercise template enrichment with corrected field names.

**What it tests:**
- Template pagination (fetches all 429 templates)
- Primary muscle group distribution
- Equipment type analysis
- Exercise type breakdown
- Template enrichment on actual workouts

**Run:**
```bash
python3 test_corrected_implementation.py
```

### `inspect_api_response.py`
Inspects the raw Hevy API response structure for exercise templates.

**What it shows:**
- Raw JSON structure from API
- All available fields
- Field analysis (which fields are populated vs null)

**Run:**
```bash
python3 inspect_api_response.py
```

### `test_api_standalone.py`
Original standalone test for API template pagination and workout notes.

**Run:**
```bash
python3 test_api_standalone.py
```

### `test_template_enrichment.py`
Integration test that uses the actual Hevy API client from the Home Assistant integration.

**Note:** Requires Home Assistant dependencies installed.

**Run:**
```bash
python3 test_template_enrichment.py
```

## Security Note

⚠️ **Never commit the `.env` file!** It contains your API key.

The `.env` file is already in `.gitignore` to prevent accidental commits.
