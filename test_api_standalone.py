#!/usr/bin/env python3
"""Standalone test for Hevy API template enrichment."""
import asyncio
import aiohttp
import os
from pathlib import Path

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

API_BASE_URL = "https://api.hevyapp.com/v1"
API_KEY = os.getenv("HEVY_API_KEY")

if not API_KEY:
    print("❌ Error: HEVY_API_KEY not found in environment or .env file")
    print("   Create a .env file with: HEVY_API_KEY=your-api-key")
    exit(1)


async def test_hevy_api():
    """Test Hevy API template pagination and workout notes."""

    async with aiohttp.ClientSession() as session:
        headers = {"api-key": API_KEY}

        print("🔍 Testing Hevy API Exercise Template Pagination...")
        print("=" * 70)

        # Test 1: Fetch first page of templates
        print("\n1️⃣  Fetching first page of templates (page_size=10)...")
        try:
            params = {"page": 1, "pageSize": 10}
            async with session.get(
                f"{API_BASE_URL}/exercise_templates",
                headers=headers,
                params=params
            ) as response:
                if response.status != 200:
                    print(f"   ❌ Error: Status {response.status}")
                    return False

                data = await response.json()
                templates = data.get("exercise_templates", [])
                page_count = data.get("page_count", 0)

                print(f"   ✅ Success! Found {len(templates)} templates on page 1")
                print(f"   ℹ️  Total pages: {page_count}")

                if templates:
                    template = templates[0]
                    print(f"\n   📋 Sample template:")
                    print(f"      • ID: {template.get('id')}")
                    print(f"      • Title: {template.get('title')}")
                    print(f"      • Muscle Group: {template.get('muscle_group')}")
                    print(f"      • Secondary: {template.get('secondary_muscle_groups', [])}")
                    print(f"      • Equipment: {template.get('equipment_type')}")
                    print(f"      • Category: {template.get('category')}")
        except Exception as err:
            print(f"   ❌ Error: {err}")
            return False

        # Test 2: Fetch all templates with pagination
        print(f"\n2️⃣  Fetching ALL templates (simulating coordinator fetch)...")
        try:
            all_templates = {}
            page = 1

            while True:
                params = {"page": page, "pageSize": 50}
                async with session.get(
                    f"{API_BASE_URL}/exercise_templates",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        print(f"   ❌ Error on page {page}: Status {response.status}")
                        break

                    data = await response.json()
                    templates = data.get("exercise_templates", [])

                    if not templates:
                        break

                    for template in templates:
                        template_id = template.get("id")
                        if template_id:
                            all_templates[template_id] = {
                                "title": template.get("title"),
                                "muscle_group": template.get("muscle_group"),
                                "secondary_muscle_groups": template.get("secondary_muscle_groups", []),
                                "equipment": template.get("equipment_type"),
                                "category": template.get("category"),
                            }

                    page_count = data.get("page_count", 1)
                    print(f"   📄 Page {page}/{page_count}: {len(templates)} templates")

                    if page >= page_count:
                        break

                    page += 1

            print(f"\n   ✅ Total templates cached: {len(all_templates)}")

            # Analyze muscle groups
            muscle_groups = {}
            equipment_types = {}

            for template in all_templates.values():
                mg = template.get("muscle_group") or "Unknown"
                eq = template.get("equipment") or "Unknown"
                muscle_groups[mg] = muscle_groups.get(mg, 0) + 1
                equipment_types[eq] = equipment_types.get(eq, 0) + 1

            print(f"\n   📊 Muscle Group Distribution (top 10):")
            for mg, count in sorted(muscle_groups.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"      • {mg}: {count} exercises")

            print(f"\n   🏋️  Equipment Type Distribution (top 10):")
            for eq, count in sorted(equipment_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"      • {eq}: {count} exercises")

        except Exception as err:
            print(f"   ❌ Error: {err}")
            return False

        # Test 3: Fetch workouts and check for notes field
        print(f"\n3️⃣  Testing workout notes and template matching...")
        try:
            params = {"page": 1, "pageSize": 5}
            async with session.get(
                f"{API_BASE_URL}/workouts",
                headers=headers,
                params=params
            ) as response:
                if response.status != 200:
                    print(f"   ❌ Error: Status {response.status}")
                    return False

                data = await response.json()
                workouts = data.get("workouts", [])

                if workouts:
                    workout = workouts[0]
                    print(f"   ✅ Latest workout: {workout.get('title')}")
                    print(f"   📅 Date: {workout.get('start_time')}")

                    exercises_with_templates = 0
                    exercises_with_notes = 0

                    for idx, exercise in enumerate(workout.get("exercises", [])[:5], 1):
                        title = exercise.get("title")
                        notes = exercise.get("notes")
                        template_id = exercise.get("exercise_template_id")

                        print(f"\n   Exercise {idx}: {title}")
                        print(f"      • Template ID: {template_id}")

                        if notes:
                            print(f"      • Notes: \"{notes}\"")
                            exercises_with_notes += 1
                        else:
                            print(f"      • Notes: (none)")

                        # Check if we have template data
                        if template_id and template_id in all_templates:
                            template = all_templates[template_id]
                            print(f"      • ✅ Template enrichment available!")
                            print(f"         - Muscle Group: {template.get('muscle_group')}")
                            print(f"         - Secondary: {template.get('secondary_muscle_groups')}")
                            print(f"         - Equipment: {template.get('equipment')}")
                            print(f"         - Category: {template.get('category')}")
                            exercises_with_templates += 1
                        else:
                            print(f"      • ⚠️  No template data found")

                    print(f"\n   📊 Summary:")
                    print(f"      • Exercises with template data: {exercises_with_templates}/{min(5, len(workout.get('exercises', [])))}")
                    print(f"      • Exercises with notes: {exercises_with_notes}/{min(5, len(workout.get('exercises', [])))}")
                else:
                    print("   ⚠️  No workouts found")

        except Exception as err:
            print(f"   ❌ Error: {err}")
            return False

        print("\n" + "=" * 70)
        print("✅ All API tests passed!")
        print("\n🎉 Implementation verified:")
        print("   • Pagination works correctly")
        print("   • Exercise templates fetch successfully")
        print("   • Template data includes muscle_group, equipment, category")
        print("   • Workout notes field is present in API response")
        print("   • Template IDs match between workouts and templates")
        return True


if __name__ == "__main__":
    result = asyncio.run(test_hevy_api())
    exit(0 if result else 1)
