"""Constants for the Hevy Workout Tracker integration."""

DOMAIN = "hevy"

# API Configuration
API_BASE_URL = "https://api.hevyapp.com/v1"
API_TIMEOUT = 30

# Config/Options Keys
CONF_API_KEY = "api_key"
CONF_UNIT_SYSTEM = "unit_system"
CONF_POLLING_INTERVAL = "polling_interval"

# Unit Systems
UNIT_SYSTEM_IMPERIAL = "imperial"
UNIT_SYSTEM_METRIC = "metric"

# Defaults
DEFAULT_POLLING_INTERVAL = 15  # minutes
DEFAULT_UNIT_SYSTEM = UNIT_SYSTEM_IMPERIAL
DEFAULT_NAME = "Hevy"

# Conversion
KG_TO_LBS = 2.20462

# Sensor Types
SENSOR_WORKOUT_COUNT = "workout_count"
SENSOR_LAST_WORKOUT_DATE = "last_workout_date"
SENSOR_LAST_WORKOUT_SUMMARY = "last_workout_summary"
SENSOR_WEEKLY_WORKOUT_COUNT = "weekly_workout_count"
SENSOR_CURRENT_STREAK = "current_streak"
BINARY_SENSOR_WORKED_OUT_TODAY = "worked_out_today"
BINARY_SENSOR_WORKED_OUT_THIS_WEEK = "worked_out_this_week"

# API Endpoints
ENDPOINT_WORKOUTS = "/workouts"
ENDPOINT_WORKOUTS_COUNT = "/workouts/count"
ENDPOINT_WORKOUTS_EVENTS = "/workouts/events"
ENDPOINT_EXERCISE_TEMPLATES = "/exercise_templates"
ENDPOINT_ROUTINES = "/routines"
