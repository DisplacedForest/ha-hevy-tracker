# Changelog

All notable changes to the Hevy Workout Tracker integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-11

### Added
- **Exercise template enrichment** - All exercise sensors now include muscle group and equipment metadata
  - `muscle_group` attribute - Primary muscle targeted (chest, shoulders, quadriceps, etc.)
  - `secondary_muscles` attribute - Secondary muscles worked (e.g., triceps, shoulders for bench press)
  - `equipment` attribute - Equipment type (barbell, dumbbell, machine, kettlebell, etc.)
  - `exercise_type` attribute - Exercise type (weight_reps, duration, reps_only, etc.)
  - 429 exercise templates cached on integration startup
- **Workout notes** - Exercise notes now exposed in sensor attributes
  - `notes` attribute added to per-exercise sensors
  - Notes visible in last workout summary sensor exercises array
- **API pagination support** - Exercise template API endpoint now supports pagination
  - Efficiently fetches all templates using page_size=50
  - Handles multi-page responses automatically
- **Template caching system** - Exercise templates fetched once on startup and cached in memory
  - O(1) lookup performance for template enrichment
  - Graceful degradation if template fetch fails
  - Logs total templates cached for verification

### Changed
- Exercise sensors now show richer metadata enabling muscle group tracking
- Foundation laid for planned muscle group summary sensors

### Technical
- Added `fetch_exercise_templates()` method to coordinator
- Template cache stored in `_exercise_templates` dict indexed by template ID
- Templates fetched before first data refresh in async_setup_entry
- Test scripts now use `.env` file for API key (security improvement)

## [0.1.0] - 2026-02-11

### Added
- Initial release of Hevy Workout Tracker integration
- API client with full async support and error handling
- DataUpdateCoordinator with configurable polling interval (5-120 minutes)
- Config flow for API key entry with validation
- Options flow for polling interval and unit system configuration (imperial/metric)
- Summary sensors:
  - `sensor.hevy_workout_count` - Total lifetime workout count
  - `sensor.hevy_last_workout_date` - Timestamp of most recent workout
  - `sensor.hevy_last_workout_summary` - Full workout summary with exercises
  - `sensor.hevy_weekly_workout_count` - Workouts in last 7 days
  - `sensor.hevy_current_streak` - Consecutive workout days (allows 1 rest day)
- Binary sensors:
  - `binary_sensor.hevy_worked_out_today` - Workout logged today
  - `binary_sensor.hevy_worked_out_this_week` - Workout in last 7 days
- Dynamic per-exercise sensors with:
  - Best set display (e.g., "35 lbs × 12" or "16 kg × 12" or "60s")
  - Full set history in attributes
  - Personal record tracking (heaviest weight, max reps)
  - Support for both weighted and timed exercises
- Weight unit support:
  - Imperial: kg to lbs conversion with 0.5 lb rounding
  - Metric: kg rounding to nearest 0.5 kg
  - User-configurable in options flow
- Total volume calculation (weight × reps) in selected unit
- Workout duration tracking
- Set-level detail with type (normal, warmup, dropset, failure)
- Device grouping for all Hevy entities
- Comprehensive error handling and logging
- HACS compatibility with metadata files

### Features
- Full set-level detail for all exercises
- Automatic PR (personal record) tracking across workout history
- Smart streak calculation supporting A-B-C training rotation
- Rich sensor attributes with complete workout data
- Support for multiple exercise types (weighted, timed, bodyweight)
- Configurable unit system (lbs or kg)
- Proper async patterns throughout
- Type hints for better IDE support
- Configurable update intervals to manage API usage

## [Unreleased]

### Planned - High Priority
- **30-day workout history sensor** - Store last 30 days of workouts with full exercise/set detail to enable calendar UI and historical analysis
  - Current limitation: Integration only exposes last workout
  - Required for: 30-day rolling calendar view, clickable workout days, workout receipt popups
  - Backend change needed: Fetch and store 30-day history as sensor attributes
- **Muscle group summary sensor** - Track which muscle groups were hit in last workout and which are due (enables LLM analysis)
  - Foundation complete: Template enrichment provides muscle group data
  - Next step: Create aggregation sensor
- **Volume per muscle group tracking** - Total chest volume, leg volume, etc. across the week for program balance monitoring
  - Foundation complete: Template enrichment provides muscle group data
  - Next step: Calculate volume per muscle group
- **Routine tracking sensors** - Show next workout in A/B/C rotation (e.g., "Day B - Pull/Hinge Focus")
- **Webhook support** - Replace polling with webhooks for real-time updates after workouts

### Planned - Low Priority
- Graph card examples for workout trends (documentation, not code)
- Superset tracking (not currently needed)
- Custom metric support (not currently needed)
