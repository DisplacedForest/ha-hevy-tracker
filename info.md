# Hevy Workout Tracker

Track your Hevy workouts in Home Assistant with rich, detailed sensor data.

## Features

- **Summary sensors** for workout count, streaks, and weekly activity
- **Muscle group tracking** - which muscles were hit, which are due, days since last trained
- **Weekly volume analysis** - volume per muscle group with exercise breakdown
- **Routine rotation** - detects next workout in your A/B/C rotation
- **Per-exercise tracking** with personal record monitoring
- **Full set-level detail** including weight, reps, and duration
- **Smart metrics** like total volume and best sets
- **30-day workout history** - service call for enriched historical data
- **Unit support** for both imperial (lbs) and metric (kg)
- **Configurable polling** from 5-120 minute intervals

## Sensors Included

### Summary
- Total workout count
- Last workout date and details
- Weekly workout count
- Current workout streak
- Muscle group summary (primary/secondary groups, muscles due)
- Weekly muscle volume (volume per group with exercise breakdown)
- Next workout (routine rotation detection)
- Worked out today (binary)
- Worked out this week (binary)

### Per-Exercise (Dynamic)
- Automatically created for each exercise
- Shows best set performance
- Tracks personal records
- Full set history in attributes
- Muscle group and equipment metadata

### Services
- `hevy.get_workout_history` - returns enriched workout data for 1-90 days

## Setup

1. Get your API key from Hevy app (Settings → Account → API Key)
2. Add integration in Home Assistant
3. Enter your API key
4. Configure polling interval and units (optional)

All workouts sync automatically!
