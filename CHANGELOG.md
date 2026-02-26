# Changelog

All notable changes to the Hevy Workout Tracker integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-02-26

### Fixed
- Fix crash when tracking PRs for cardio exercises (treadmill, etc.) where reps is null in the API response (#2)

## [1.0.0] - 2026-02-12

### Added
- **Workout summaries attribute** on `sensor.hevy_last_workout_date`
  - Date-keyed dict of workout details for the full 30-day window
  - Each entry includes title, duration, total volume, exercise count, and full exercise/set detail
  - Enables dashboard cards to show per-day workout info when a date is tapped
- **Personal Records dashboard card** example in README
- Brand assets for HACS default repository submission

### Changed
- Added `integration_type: hub` to manifest for HACS compliance
- Updated CI workflows: `actions/checkout` v3 → v4, added `workflow_dispatch` trigger, added `permissions: {}` for security
- Fixed muscle recovery screenshot path in README

### Removed
- Removed planned/unreleased features section from changelog

## [0.3.0] - 2026-02-11

### Added
- **Muscle group summary sensor** - `sensor.hevy_muscle_group_summary`
  - State: comma-separated primary muscle groups from last workout (e.g., "chest, shoulders, quadriceps")
  - `last_workout_primary_groups` attribute - list of primary muscle groups hit
  - `last_workout_secondary_groups` attribute - list of secondary muscles worked
  - `days_since_last` attribute - dict mapping each muscle group to days since last trained
  - `muscles_due` attribute - list of muscle groups not trained in 3+ days
- **Weekly muscle volume sensor** - `sensor.hevy_weekly_muscle_volume`
  - State: total volume across all muscle groups for the last 7 days
  - `muscle_groups` attribute - volume breakdown per muscle group (e.g., chest: 1860, quads: 2025)
  - `exercise_breakdown` attribute - per-exercise volume detail within each muscle group
  - `total_sets` and `total_workouts` attributes
  - Excludes warmup sets and bodyweight/timed exercises from volume calculation
  - Assigns volume to primary muscle group only (no double-counting)
- **Next workout sensor** - `sensor.hevy_next_workout`
  - State: next routine title in rotation (e.g., "Day B - Pull/Hinge Focus")
  - `rotation_position` / `rotation_total` attributes (e.g., 2 of 3)
  - `exercises_preview` attribute - list of exercises in the upcoming routine
  - `last_workout_title` / `last_workout_routine_id` attributes
  - Routine detection via `routine_id` field with index-based rotation
- **30-day workout history** - Coordinator now fetches full 30-day window via pagination
  - Dynamic pagination: stops when workouts are older than 30 days or after 10 pages (100 workouts max)
  - All existing sensors benefit from deeper history (streaks, PRs, weekly counts)
- **Routine caching** - Routines fetched and cached on startup (follows template caching pattern)
  - Stores routine id, title, and exercise list for rotation detection
  - Graceful degradation if routine fetch fails
- **`hevy.get_workout_history` service call** - Returns enriched workout data via Developer Tools > Services
  - Configurable `days` parameter (1-90, default 30)
  - Returns full exercise and set detail with muscle group enrichment
  - Includes summary: total workouts, total volume, avg duration, avg volume per workout
  - Uses `SupportsResponse.ONLY` pattern (response-only service)

### Changed
- Workout history expanded from 10 workouts to full 30-day rolling window
- API calls per cycle increased from ~2 to ~4-5 (count + 3-4 pages) to support pagination
- `[Unreleased]` planned items for muscle groups, volume tracking, routine tracking, and 30-day history are now implemented

### Technical
- New files: `services.py` (service handler), `services.yaml` (service schema)
- Added `fetch_routines()`, `_fetch_30_day_workouts()`, `_detect_next_workout()`, `_aggregate_muscle_groups()`, `_calculate_weekly_muscle_volume()` to coordinator
- New constants: `SENSOR_MUSCLE_GROUP_SUMMARY`, `SENSOR_WEEKLY_MUSCLE_VOLUME`, `SENSOR_NEXT_WORKOUT`, `MUSCLE_DUE_THRESHOLD_DAYS`, `MAX_WORKOUT_PAGES`, `WORKOUT_HISTORY_DAYS`
- Service registered in `async_setup_entry()`, unregistered in `async_unload_entry()`

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

