# Hevy Workout Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A comprehensive Home Assistant integration for tracking your Hevy workouts with rich, detailed sensor data.

## Features

- **Rich Workout Data** - Full set-level detail with weight, reps, and duration tracking
- **Summary Sensors** - Workout count, streaks, weekly activity
- **Per-Exercise Tracking** - Individual sensors for each exercise with personal records
- **Smart Metrics** - Total volume, best sets, and workout duration
- **Automatic Updates** - Configurable polling interval (5-120 minutes)
- **Unit Support** - Display in imperial (lbs) or metric (kg)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL with category "Integration"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Download the `hevy` folder from this repository
2. Copy it to your `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **Hevy Workout Tracker**
4. Enter your Hevy API key

### Getting Your API Key

1. Open the Hevy app
2. Go to **Settings** → **Account**
3. Scroll to **API Key**
4. Copy your API key

## Sensors

### Summary Sensors

| Sensor | Description | State |
|--------|-------------|-------|
| `sensor.hevy_workout_count` | Total lifetime workouts | Integer count |
| `sensor.hevy_last_workout_date` | Timestamp of most recent workout | ISO datetime |
| `sensor.hevy_last_workout_summary` | Full summary of last workout | Workout title |
| `sensor.hevy_weekly_workout_count` | Workouts in last 7 days | Integer count |
| `sensor.hevy_current_streak` | Consecutive workout days | Days (allows 1 rest day) |

### Binary Sensors

| Sensor | Description |
|--------|-------------|
| `binary_sensor.hevy_worked_out_today` | On if workout logged today |
| `binary_sensor.hevy_worked_out_this_week` | On if any workout in last 7 days |

### Per-Exercise Sensors

Dynamically created for each unique exercise:

**Example:** `sensor.hevy_bench_press_dumbbell`

**State:** Best set (e.g., "35 lbs × 12" or "60s")

**Attributes:**
- `last_workout_date` - ISO datetime of last workout
- `last_workout_sets` - List of all sets from last workout
- `weight` - Most recent weight used
- `weight_unit` - Unit system (lbs or kg)
- `total_reps` - Total reps from last workout
- `total_sets` - Number of sets performed
- `personal_record_weight` - Heaviest weight ever used
- `personal_record_reps` - Most reps at PR weight
- `exercise_template_id` - Hevy exercise ID

## Detailed Sensor Attributes

### Last Workout Summary Attributes

```yaml
date: "2026-02-11T16:21:10+00:00"
duration_minutes: 4.7
total_volume: 1158.5
total_volume_unit: "lbs"
exercise_count: 2
exercises:
  - name: "Bench Press (Dumbbell)"
    sets:
      - type: "normal"
        weight: 35.0
        weight_unit: "lbs"
        reps: 12
        duration_seconds: null
      - type: "normal"
        weight: 35.0
        weight_unit: "lbs"
        reps: 12
        duration_seconds: null
    best_set: "35 lbs × 12"
    total_reps: 24
  - name: "Plank"
    sets:
      - type: "normal"
        weight: null
        weight_unit: "lbs"
        reps: null
        duration_seconds: 60
    best_set: "1m 00s"
    total_duration_seconds: 60
```

## Configuration Options

Access via **Devices & Services** → **Hevy Workout Tracker** → **Configure**

- **Polling Interval** - How often to fetch new data (5-120 minutes, default: 15)
- **Unit System** - Display units (imperial/metric, default: imperial)

## Weight Conversion

- All weights displayed in lbs (converted from kg)
- Rounded to nearest 0.5 lbs for readability
- Conversion factor: 1 kg = 2.20462 lbs

## API Details

This integration uses the official Hevy API:
- Base URL: `https://api.hevyapp.com/v1/`
- Authentication: API key header
- Rate limiting: Respects polling interval

## Use Cases

### Automation Examples

**Workout Streak Notification:**
```yaml
automation:
  - alias: "Workout Streak Milestone"
    trigger:
      - platform: numeric_state
        entity_id: sensor.hevy_current_streak
        above: 7
    action:
      - service: notify.mobile_app
        data:
          message: "7 day workout streak! Keep it up!"
```

**Rest Day Reminder:**
```yaml
automation:
  - alias: "Rest Day Reminder"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.hevy_worked_out_today
        state: "off"
      - condition: numeric_state
        entity_id: sensor.hevy_current_streak
        above: 0
    action:
      - service: notify.mobile_app
        data:
          message: "Don't break your streak! Time for a workout."
```

**Personal Record Alert:**
```yaml
automation:
  - alias: "New PR Notification"
    trigger:
      - platform: state
        entity_id: sensor.hevy_bench_press_dumbbell
        attribute: personal_record_weight
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.personal_record_weight > trigger.from_state.attributes.personal_record_weight }}"
    action:
      - service: notify.mobile_app
        data:
          message: "New PR on Bench Press: {{ trigger.to_state.attributes.personal_record_weight }} {{ trigger.to_state.attributes.weight_unit }}!"
```

### Dashboard Card Example

```yaml
type: entities
title: Hevy Workout Stats
entities:
  - entity: sensor.hevy_current_streak
    name: Current Streak
  - entity: sensor.hevy_weekly_workout_count
    name: This Week
  - entity: sensor.hevy_last_workout_summary
    name: Last Workout
  - entity: sensor.hevy_bench_press_dumbbell
    name: Bench Press PR
  - entity: binary_sensor.hevy_worked_out_today
    name: Worked Out Today
```

## Troubleshooting

**Integration not showing up:**
- Ensure you've restarted Home Assistant after installation
- Check logs for errors: Settings → System → Logs

**Invalid API key error:**
- Verify your API key in the Hevy app
- Try generating a new API key

**Sensors not updating:**
- Check your polling interval setting
- Verify internet connection
- Check Home Assistant logs for API errors

**Missing exercises:**
- Sensors are created dynamically on first fetch
- Wait for one polling cycle after adding new exercises
- Check that the exercise has data in your Hevy account

## Support

For issues, feature requests, or contributions:
- GitHub Issues: [Report an issue](https://github.com/zachary/hevy-hass/issues)
- Home Assistant Community: [Discussion thread](https://community.home-assistant.io/)

## Credits

Built from scratch using proper Home Assistant integration patterns, replacing the basic implementation from [HA-hevy](https://github.com/hudsonbrendon/HA-hevy).

## License

MIT License - see LICENSE file for details
