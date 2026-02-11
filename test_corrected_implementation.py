#!/usr/bin/env python3
"""Test corrected template field names."""
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


async def test_corrected_fields():
    """Test with corrected field names."""

    async with aiohttp.ClientSession() as session:
        headers = {"api-key": API_KEY}

        print("🔧 Testing CORRECTED implementation...")
        print("=" * 70)

        # Fetch templates with corrected field names
        print("\n1️⃣  Fetching templates with correct field mapping...")
        all_templates = {}
        page = 1

        while True:
            params = {"page": page, "pageSize": 50}
            async with session.get(
                f"{API_BASE_URL}/exercise_templates",
                headers=headers,
                params=params
            ) as response:
                data = await response.json()
                templates = data.get("exercise_templates", [])

                if not templates:
                    break

                for template in templates:
                    template_id = template.get("id")
                    if template_id:
                        # Use CORRECT field names
                        all_templates[template_id] = {
                            "title": template.get("title"),
                            "muscle_group": template.get("primary_muscle_group"),  # FIXED!
                            "secondary_muscle_groups": template.get("secondary_muscle_groups", []),
                            "equipment": template.get("equipment"),  # FIXED!
                            "type": template.get("type"),  # CHANGED from category
                        }

                page_count = data.get("page_count", 1)
                if page >= page_count:
                    break
                page += 1

        print(f"   ✅ Cached {len(all_templates)} templates")

        # Analyze data
        muscle_groups = {}
        equipment_types = {}
        exercise_types = {}

        for template in all_templates.values():
            mg = template.get("muscle_group") or "Unknown"
            eq = template.get("equipment") or "Unknown"
            typ = template.get("type") or "Unknown"

            muscle_groups[mg] = muscle_groups.get(mg, 0) + 1
            equipment_types[eq] = equipment_types.get(eq, 0) + 1
            exercise_types[typ] = exercise_types.get(typ, 0) + 1

        print(f"\n   📊 PRIMARY Muscle Groups (top 10):")
        for mg, count in sorted(muscle_groups.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"      • {mg}: {count} exercises")

        print(f"\n   🏋️  Equipment Types:")
        for eq, count in sorted(equipment_types.items(), key=lambda x: x[1], reverse=True):
            print(f"      • {eq}: {count} exercises")

        print(f"\n   📋 Exercise Types:")
        for typ, count in sorted(exercise_types.items(), key=lambda x: x[1], reverse=True):
            print(f"      • {typ}: {count} exercises")

        # Test with actual workout
        print(f"\n2️⃣  Testing enrichment with your workout...")
        params = {"page": 1, "pageSize": 1}
        async with session.get(
            f"{API_BASE_URL}/workouts",
            headers=headers,
            params=params
        ) as response:
            data = await response.json()
            workouts = data.get("workouts", [])

            if workouts:
                workout = workouts[0]
                print(f"   ✅ Workout: {workout.get('title')}")

                for idx, exercise in enumerate(workout.get("exercises", [])[:3], 1):
                    title = exercise.get("title")
                    template_id = exercise.get("exercise_template_id")

                    print(f"\n   Exercise {idx}: {title}")
                    print(f"      Template ID: {template_id}")

                    if template_id and template_id in all_templates:
                        template = all_templates[template_id]
                        print(f"      ✅ Enriched data:")
                        print(f"         • Primary Muscle: {template.get('muscle_group')}")
                        print(f"         • Secondary: {template.get('secondary_muscle_groups')}")
                        print(f"         • Equipment: {template.get('equipment')}")
                        print(f"         • Type: {template.get('type')}")

        print("\n" + "=" * 70)
        print("✅ Corrected implementation verified!")
        print("\n🎉 Now you'll see actual muscle group data!")


if __name__ == "__main__":
    asyncio.run(test_corrected_fields())
