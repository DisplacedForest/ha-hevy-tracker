# Hevy Workout Tracker

Track your [Hevy](https://www.hevyapp.com/) workouts in Home Assistant with rich sensor data, muscle recovery tracking, and personal record monitoring.

> **Requires a [Hevy Pro](https://www.hevyapp.com/pro) subscription** for API access.

## Features

- **Summary sensors** — workout count, streaks, weekly activity, and worked out today/this week
- **Per-exercise sensors** — automatically created for each exercise, with personal records and full set history
- **Muscle group tracking** — which muscles were hit, days since last trained, and which are due
- **Weekly volume analysis** — volume per muscle group with exercise breakdown
- **Routine rotation** — detects the next workout in your A/B/C rotation
- **30-day history** — service call returning enriched workout data for use in automations
- **Unit support** — imperial (lbs) or metric (kg)
- **Configurable polling** — 5 to 120 minute intervals

## Setup

1. Get your API key from the Hevy app: **Profile → Settings → Developer**
2. Add the integration in Home Assistant
3. Enter your API key and configure your preferences

See the [full documentation](https://github.com/DisplacedForest/ha-hevy-tracker) for sensor references, dashboard card examples, and automation ideas.
