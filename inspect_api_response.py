#!/usr/bin/env python3
"""Inspect raw Hevy API response for exercise templates."""
import asyncio
import aiohttp
import json
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


async def inspect_templates():
    """Inspect raw template API response."""

    async with aiohttp.ClientSession() as session:
        headers = {"api-key": API_KEY}

        print("🔍 Inspecting raw API response for exercise templates...\n")
        print("=" * 70)

        # Fetch first page
        params = {"page": 1, "pageSize": 5}
        async with session.get(
            f"{API_BASE_URL}/exercise_templates",
            headers=headers,
            params=params
        ) as response:
            data = await response.json()

            print("\n📋 Top-level keys in response:")
            print(json.dumps(list(data.keys()), indent=2))

            print(f"\n📊 Page info:")
            print(f"   • page: {data.get('page')}")
            print(f"   • page_count: {data.get('page_count')}")
            print(f"   • Total templates on this page: {len(data.get('exercise_templates', []))}")

            templates = data.get("exercise_templates", [])

            if templates:
                print(f"\n" + "=" * 70)
                print("📝 First 3 templates (full structure):\n")

                for idx, template in enumerate(templates[:3], 1):
                    print(f"Template {idx}: {template.get('title')}")
                    print("-" * 70)
                    print(json.dumps(template, indent=2, default=str))
                    print()

                print("=" * 70)
                print("\n🔑 All unique keys across all templates on this page:")
                all_keys = set()
                for template in templates:
                    all_keys.update(template.keys())
                print(json.dumps(sorted(list(all_keys)), indent=2))

                print("\n" + "=" * 70)
                print("\n📊 Field analysis:")

                # Analyze each field
                fields_to_check = [
                    'muscle_group',
                    'primary_muscle_group',
                    'muscle_groups',
                    'primary_muscle_groups',
                    'secondary_muscle_groups',
                    'equipment',
                    'equipment_type',
                    'category'
                ]

                for field in fields_to_check:
                    non_null_count = sum(1 for t in templates if t.get(field) not in (None, '', []))
                    sample_value = next((t.get(field) for t in templates if t.get(field) not in (None, '', [])), None)

                    if non_null_count > 0:
                        print(f"\n   ✅ '{field}':")
                        print(f"      • Non-null: {non_null_count}/{len(templates)}")
                        print(f"      • Sample: {sample_value}")
                    else:
                        if field in templates[0]:
                            print(f"\n   ⚠️  '{field}': exists but all values are null/empty")
                        else:
                            print(f"\n   ❌ '{field}': field doesn't exist")


if __name__ == "__main__":
    asyncio.run(inspect_templates())
