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
METERS_TO_MILES = 0.000621371
METERS_TO_KM = 0.001

# Sensor Types
SENSOR_WORKOUT_COUNT = "workout_count"
SENSOR_LAST_WORKOUT_DATE = "last_workout_date"
SENSOR_LAST_WORKOUT_SUMMARY = "last_workout_summary"
SENSOR_WEEKLY_WORKOUT_COUNT = "weekly_workout_count"
SENSOR_CURRENT_STREAK = "current_streak"
BINARY_SENSOR_WORKED_OUT_TODAY = "worked_out_today"
BINARY_SENSOR_WORKED_OUT_THIS_WEEK = "worked_out_this_week"
SENSOR_MUSCLE_GROUP_SUMMARY = "muscle_group_summary"
SENSOR_WEEKLY_MUSCLE_VOLUME = "weekly_muscle_volume"
SENSOR_WEEKLY_DISTANCE = "weekly_distance"
SENSOR_NEXT_WORKOUT = "next_workout"
SENSOR_LAST_BODY_MEASUREMENT = "last_body_measurement"

BODY_MEASUREMENT_FIELDS: dict[str, tuple[str, str, str]] = {
    "weight_kg": ("body_weight", "Body weight", "weight"),
    "lean_mass_kg": ("lean_body_mass", "Lean body mass", "weight"),
    "fat_percent": ("body_fat", "Body fat", "percent"),
    "neck_cm": ("neck", "Neck", "length"),
    "shoulder_cm": ("shoulder", "Shoulder", "length"),
    "chest_cm": ("chest", "Chest", "length"),
    "left_bicep_cm": ("left_bicep", "Left bicep", "length"),
    "right_bicep_cm": ("right_bicep", "Right bicep", "length"),
    "left_forearm_cm": ("left_forearm", "Left forearm", "length"),
    "right_forearm_cm": ("right_forearm", "Right forearm", "length"),
    "abdomen": ("abdomen", "Abdomen", "length"),
    "waist": ("waist", "Waist", "length"),
    "hips": ("hips", "Hips", "length"),
    "left_thigh": ("left_thigh", "Left thigh", "length"),
    "right_thigh": ("right_thigh", "Right thigh", "length"),
    "left_calf": ("left_calf", "Left calf", "length"),
    "right_calf": ("right_calf", "Right calf", "length"),
}
MAX_BODY_MEASUREMENT_PAGES = 5
BODY_MEASUREMENT_HISTORY = 30

MUSCLE_DUE_THRESHOLD_DAYS = 3
MAX_WORKOUT_PAGES = 10  # Safety cap for pagination
WORKOUT_HISTORY_DAYS = 30

# API Endpoints
ENDPOINT_WORKOUTS = "/workouts"
ENDPOINT_WORKOUTS_COUNT = "/workouts/count"
ENDPOINT_WORKOUTS_EVENTS = "/workouts/events"
ENDPOINT_EXERCISE_TEMPLATES = "/exercise_templates"
ENDPOINT_ROUTINES = "/routines"
