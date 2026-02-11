#!/usr/bin/env python3
"""Test script for Hevy exercise template enrichment."""
import asyncio
import sys
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

# Add custom_components to path
sys.path.insert(0, '/Users/zachary/Desktop/Projects/Hevy')

from custom_components.hevy.api import HevyApiClient


async def test_template_pagination():
    """Test exercise template pagination."""
    api_key = os.getenv("HEVY_API_KEY")

    if not api_key:
        print("❌ Error: HEVY_API_KEY not found in environment or .env file")
        print("   Create a .env file with: HEVY_API_KEY=your-api-key")
        return False

    async with aiohttp.ClientSession() as session:
        client = HevyApiClient(api_key, session)

        print("🔍 Testing Exercise Template Pagination...")
        print("=" * 60)

        # Test fetching first page
        print("\n1. Fetching first page (page_size=10)...")
        try:
            page1_data = await client.get_exercise_templates(page=1, page_size=10)
            templates_p1 = page1_data.get("exercise_templates", [])
            page_count = page1_data.get("page_count", 0)

            print(f"   ✅ Success! Found {len(templates_p1)} templates on page 1")
            print(f"   ℹ️  Total pages: {page_count}")

            if templates_p1:
                template = templates_p1[0]
                print(f"\n   Sample template:")
                print(f"   - ID: {template.get('id')}")
                print(f"   - Title: {template.get('title')}")
                print(f"   - Muscle Group: {template.get('muscle_group')}")
                print(f"   - Secondary Muscles: {template.get('secondary_muscle_groups')}")
                print(f"   - Equipment: {template.get('equipment_type')}")
                print(f"   - Category: {template.get('category')}")
        except Exception as err:
            print(f"   ❌ Error: {err}")
            return False

        # Test fetching all pages
        print(f"\n2. Fetching all templates (page_size=50)...")
        try:
            all_templates = {}
            page = 1

            while True:
                data = await client.get_exercise_templates(page=page, page_size=50)
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

            # Show muscle group distribution
            muscle_groups = {}
            for template in all_templates.values():
                mg = template.get("muscle_group") or "Unknown"
                muscle_groups[mg] = muscle_groups.get(mg, 0) + 1

            print(f"\n   📊 Muscle Group Distribution:")
            for mg, count in sorted(muscle_groups.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"      - {mg}: {count} exercises")

        except Exception as err:
            print(f"   ❌ Error: {err}")
            return False

        # Test fetching workout data with notes
        print(f"\n3. Testing workout notes field...")
        try:
            workouts_data = await client.get_workouts(page=1, page_size=5)
            workouts = workouts_data.get("workouts", [])

            if workouts:
                workout = workouts[0]
                print(f"   ✅ Latest workout: {workout.get('title')}")

                for exercise in workout.get("exercises", [])[:3]:
                    title = exercise.get("title")
                    notes = exercise.get("notes")
                    template_id = exercise.get("exercise_template_id")

                    print(f"\n   Exercise: {title}")
                    print(f"   - Template ID: {template_id}")
                    print(f"   - Notes: {notes if notes else '(none)'}")

                    # Check if we have template data for this exercise
                    if template_id and template_id in all_templates:
                        template = all_templates[template_id]
                        print(f"   - ✅ Template found!")
                        print(f"     • Muscle Group: {template.get('muscle_group')}")
                        print(f"     • Equipment: {template.get('equipment')}")
            else:
                print("   ⚠️  No workouts found")

        except Exception as err:
            print(f"   ❌ Error: {err}")
            return False

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        return True


if __name__ == "__main__":
    result = asyncio.run(test_template_pagination())
    sys.exit(0 if result else 1)
