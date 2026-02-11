#!/usr/bin/env python3
"""Simple script to test Hevy API connection.

Usage:
    python test_api.py YOUR_API_KEY
"""
import asyncio
import sys
from typing import Any

import aiohttp


async def test_hevy_api(api_key: str) -> None:
    """Test Hevy API connection and data retrieval.

    Args:
        api_key: Your Hevy API key
    """
    base_url = "https://api.hevyapp.com/v1"
    headers = {"api-key": api_key}

    async with aiohttp.ClientSession() as session:
        # Test 1: Get workout count
        print("=" * 60)
        print("TEST 1: Get Workout Count")
        print("=" * 60)
        try:
            async with session.get(
                f"{base_url}/workouts/count", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[SUCCESS] Workout count: {data.get('workout_count', 0)}")
                else:
                    print(f"[FAILED] Status {response.status}")
                    print(await response.text())
        except Exception as err:
            print(f"[ERROR] {err}")

        # Test 2: Get recent workouts
        print("\n" + "=" * 60)
        print("TEST 2: Get Recent Workouts")
        print("=" * 60)
        try:
            async with session.get(
                f"{base_url}/workouts",
                headers=headers,
                params={"page": 1, "pageSize": 3},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    workouts = data.get("workouts", [])
                    print(f"[SUCCESS] Found {len(workouts)} workouts")
                    for i, workout in enumerate(workouts, 1):
                        print(f"  {i}. {workout.get('title', 'Untitled')}")
                        print(f"     Date: {workout.get('start_time', 'Unknown')}")
                else:
                    print(f"[FAILED] Status {response.status}")
        except Exception as err:
            print(f"[ERROR] {err}")

        # Test 3: Get workout events with full detail
        print("\n" + "=" * 60)
        print("TEST 3: Get Workout Events (Full Detail)")
        print("=" * 60)
        try:
            async with session.get(
                f"{base_url}/workouts/events",
                headers=headers,
                params={"page": 1, "pageSize": 1},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get("events", [])
                    print(f"[SUCCESS] Found {len(events)} events")

                    if events:
                        event = events[0]
                        workout = event.get("workout", {})
                        exercises = workout.get("exercises", [])

                        print(f"\nLast Workout: {workout.get('title', 'Untitled')}")
                        print(f"Date: {workout.get('start_time', 'Unknown')}")
                        print(f"Exercises: {len(exercises)}")

                        for exercise in exercises:
                            print(f"\n  - {exercise.get('title', 'Unknown')}")
                            sets = exercise.get("sets", [])
                            print(f"    Sets: {len(sets)}")

                            for j, set_data in enumerate(sets, 1):
                                weight_kg = set_data.get("weight_kg")
                                reps = set_data.get("reps")
                                duration = set_data.get("duration_seconds")

                                if weight_kg and reps:
                                    weight_lbs = round(weight_kg * 2.20462 * 2) / 2
                                    print(f"      Set {j}: {weight_lbs} lbs × {reps}")
                                elif duration:
                                    print(f"      Set {j}: {duration}s")
                                else:
                                    print(f"      Set {j}: Bodyweight × {reps or '?'}")
                else:
                    print(f"[FAILED] Status {response.status}")
        except Exception as err:
            print(f"[ERROR] {err}")

        print("\n" + "=" * 60)
        print("Tests Complete!")
        print("=" * 60)
        print("\nIf all tests passed, your API key is valid and ready to use")
        print("with the Home Assistant integration.")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python test_api.py YOUR_API_KEY")
        sys.exit(1)

    api_key = sys.argv[1]
    asyncio.run(test_hevy_api(api_key))


if __name__ == "__main__":
    main()
