# Development Guide

## Testing the Integration

### 1. Copy to Home Assistant

Copy the `custom_components/hevy` folder to your Home Assistant `config/custom_components/` directory:

```bash
# If using Home Assistant OS or Container
cp -r custom_components/hevy /path/to/homeassistant/config/custom_components/

# If using HASS.io add-on
cp -r custom_components/hevy /config/custom_components/
```

### 2. Restart Home Assistant

Restart Home Assistant to load the integration:
- Settings → System → Restart

### 3. Add Integration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Hevy Workout Tracker"
4. Enter your Hevy API key

### 4. Verify Sensors

Check that sensors are created:
- Developer Tools → States
- Filter by "hevy"

You should see:
- `sensor.hevy_workout_count`
- `sensor.hevy_last_workout_date`
- `sensor.hevy_last_workout_summary`
- `sensor.hevy_weekly_workout_count`
- `sensor.hevy_current_streak`
- `sensor.hevy_muscle_group_summary`
- `sensor.hevy_weekly_muscle_volume`
- `sensor.hevy_next_workout`
- `binary_sensor.hevy_worked_out_today`
- `binary_sensor.hevy_worked_out_this_week`
- Plus individual exercise sensors

## Code Quality

### Type Checking

```bash
mypy custom_components/hevy
```

### Linting

```bash
pylint custom_components/hevy
```

### Formatting

```bash
black custom_components/hevy
```

## API Testing

### Manual API Testing

Test API calls directly:

```python
import asyncio
import aiohttp
from custom_components.hevy.api import HevyApiClient

async def test_api():
    async with aiohttp.ClientSession() as session:
        client = HevyApiClient("YOUR_API_KEY", session)

        # Test workout count
        count = await client.get_workout_count()
        print(f"Workout count: {count}")

        # Test workout events
        events = await client.get_workout_events(page=1, page_size=5)
        print(f"Events: {events}")

asyncio.run(test_api())
```

Note: All weight data is stored internally in kg and converted to the user's preferred unit system (lbs or kg) during sensor updates.

### Curl Testing

```bash
# Get workout count
curl -H "api-key: YOUR_API_KEY" https://api.hevyapp.com/v1/workouts/count

# Get recent workouts
curl -H "api-key: YOUR_API_KEY" "https://api.hevyapp.com/v1/workouts?page=1&pageSize=5"

# Get workout events
curl -H "api-key: YOUR_API_KEY" "https://api.hevyapp.com/v1/workouts/events?page=1&pageSize=5"
```

## Debugging

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hevy: debug
```

### Check Logs

- Settings → System → Logs
- Search for "hevy"

### Common Issues

**Sensors not updating:**
- Check coordinator update interval
- Verify API key is valid
- Check network connectivity

**Missing exercise sensors:**
- Ensure workouts contain exercise data
- Wait for one polling cycle
- Check coordinator data in debug logs

**Weight conversion issues:**
- Verify KG_TO_LBS constant (2.20462)
- Check rounding logic in coordinator

## File Structure

```
custom_components/hevy/
├── __init__.py           # Integration setup, platform forwarding, service registration
├── api.py                # Hevy API client (async, error handling)
├── config_flow.py        # UI config flow for API key
├── const.py              # Constants (domain, URLs, defaults, thresholds)
├── coordinator.py        # DataUpdateCoordinator (polling, data processing, aggregation)
├── sensor.py             # All sensor entity definitions (summary, exercise, muscle, volume, routine)
├── services.py           # Service call handlers (workout history)
├── services.yaml         # Service schema for HA UI
├── manifest.json         # Integration metadata for HA/HACS
├── strings.json          # UI strings for config flow
└── translations/
    └── en.json           # English translations
```

## Key Components

### API Client (`api.py`)
- Async HTTP requests with aiohttp
- Error handling (auth, timeouts, API errors)
- Endpoints: workouts, events, count, templates, routines

### Coordinator (`coordinator.py`)
- Fetches data every N minutes (configurable)
- 30-day workout history via paginated API calls
- Processes workouts (weight conversion, PRs, streaks)
- Calculates metrics (volume, duration, best sets)
- Muscle group aggregation (days since last trained, muscles due)
- Weekly volume per muscle group (primary only, excludes warmups)
- Routine rotation detection via `routine_id` matching
- Caches exercise templates and routines on startup

### Sensors (`sensor.py`)
- Summary sensors (static)
- Muscle group summary sensor (primary/secondary groups, muscles due)
- Weekly muscle volume sensor (volume per group with exercise breakdown)
- Next workout sensor (routine rotation with exercises preview)
- Binary sensors (worked out today/week)
- Exercise sensors (dynamic, created per exercise)
- Rich attributes with set-level detail

### Services (`services.py`)
- `hevy.get_workout_history` - enriched workout history for 1-90 days
- Uses `SupportsResponse.ONLY` pattern for response-only service calls
- Returns summary stats + full workout/exercise/set detail

### Config Flow (`config_flow.py`)
- User step: API key entry + validation
- Options flow: polling interval + unit system
- Error handling with user-friendly messages

## Weight Conversion Logic

All weights from Hevy API are in kg with high precision. The integration stores PRs in kg internally but converts for display based on user preference:

**For Imperial (lbs):**
1. Converts to lbs: `weight_kg * 2.20462`
2. Rounds to nearest 0.5 lbs: `round(weight_lbs * 2) / 2`
3. Displays as float (e.g., 35.0 lbs, 37.5 lbs)

Example: `15.87575183024739 kg → 35.0 lbs`

**For Metric (kg):**
1. Rounds to nearest 0.5 kg: `round(weight_kg * 2) / 2`
2. Displays as float (e.g., 16.0 kg, 16.5 kg)

Example: `15.87575183024739 kg → 16.0 kg`

## Streak Calculation

The streak algorithm:
1. Sorts workouts by date (most recent first)
2. Checks if streak is active (workout today or yesterday)
3. Counts consecutive days, allowing 1 rest day gap
4. Breaks on 2+ day gaps

This supports A-B-C rotation training (e.g., lift, rest, lift, rest, lift).

## Testing Checklist

- [ ] API key validation works
- [ ] Config flow completes successfully
- [ ] Options flow updates settings
- [ ] All summary sensors created
- [ ] Binary sensors show correct state
- [ ] Exercise sensors created dynamically
- [ ] Weight conversion accurate (kg → lbs)
- [ ] Personal records tracked correctly
- [ ] Streak calculation accurate
- [ ] Attributes populated correctly
- [ ] Device info groups entities
- [ ] Update interval configurable
- [ ] Errors handled gracefully
- [ ] Muscle group summary shows primary/secondary groups from last workout
- [ ] `muscles_due` lists groups not trained in 3+ days
- [ ] Weekly muscle volume excludes warmup sets and bodyweight exercises
- [ ] Volume assigned to primary muscle group only (no double-counting)
- [ ] Next workout shows correct routine rotation
- [ ] `exercises_preview` lists exercises for the upcoming routine
- [ ] `hevy.get_workout_history` service returns enriched data via Developer Tools
- [ ] 30-day pagination stops at date cutoff or page cap
- [ ] Routine cache populates on startup (check logs)
- [ ] Graceful degradation if routines fetch fails

## Release Process

1. Update version in `manifest.json`
2. Update CHANGELOG.md
3. Tag release: `git tag v1.0.0`
4. Push to GitHub: `git push --tags`
5. Create GitHub release with notes
6. HACS will auto-detect new version
