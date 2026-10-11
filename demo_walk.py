"""Outdoor Walk Demonstration Script for TrailBuddy Local.

Simulates an authentic end-to-end user session:
1. Request a 10-minute mindful outdoor mission.
2. Generate and validate the mission using local Ollama (qwen2.5:3b).
3. Display the clean 'Go Outside Mode' card.
4. Record mission completion and a nature journal reflection into SQLite.
5. Display the updated non-gamified progress summary.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.schemas import MissionRequest
from src.mission_generator import MissionGenerator
from src.storage import StorageManager
from src.privacy import verify_privacy_posture


def run_demo():
    print("=" * 65)
    print("🌿 TrailBuddy Local — Hacktoberfest 2026 Week 1 Demonstration")
    print("=" * 65)

    # 1. Privacy Audit
    posture = verify_privacy_posture()
    print("\n[1] Privacy Posture Verification:")
    print(f"    - Telemetry Disabled: {posture['telemetry_disabled']}")
    print(f"    - External Calls Blocked: {posture['external_network_blocked']}")
    print(f"    - GPS Disabled: {posture['gps_disabled']}")
    print(f"    - Ollama Endpoint: Localhost ({posture['ollama_local_only']})")
    assert posture["compliant"] is True
    print("    -> Privacy Verification: PASS (Zero Cloud Telemetry)")

    # 2. Mission Generation
    storage = StorageManager()
    generator = MissionGenerator()

    req = MissionRequest(
        duration_minutes=10,
        interest="mindfulness",
        difficulty="easy",
        environment="garden",
        accessibility="Seated pauses, level terrain",
    )

    print("\n[2] Generating Personalized Outdoor Mission via Local Qwen 2.5 3B...")
    print(f"    - Requested Time: {req.duration_minutes} minutes")
    print(f"    - Interest: {req.interest}")
    print(f"    - Environment: {req.environment}")
    print(f"    - Accessibility: {req.accessibility}")

    mission = generator.generate_mission(req)
    storage.save_mission(mission)

    print("\n[3] 'Go Outside Mode' Mission Card:")
    print(f"    Title: {mission.title}")
    print(f"    Duration: {mission.duration_minutes} minutes")
    print(f"    Description: {mission.description}")
    print("    Tasks to Complete:")
    for i, t in enumerate(mission.tasks, 1):
        print(f"      {i}. {t}")
    if mission.required_items:
        print(f"    Items: {', '.join(mission.required_items)}")
    print("    Safety Reminders:")
    for s in mission.safety_reminders:
        print(f"      - {s}")
    if mission.reflection_question:
        print(f"    Contemplation Prompt: \"{mission.reflection_question}\"")

    print("\n    >>> ACTION: [I'm Heading Outside] <<<")
    print("    *User locks screen and spends 10 mindful minutes outside.*")

    # 4. Mission Completion & Nature Journal
    print("\n[4] Recording Completion & Nature Journal Reflection...")
    reflection = (
        "Sat near the garden fern. The air was cool and crisp. "
        "Noticed five distinct shades of green on the underside of the leaves. "
        "Felt deeply refreshed after leaving the monitor behind."
    )
    completed_mission = storage.complete_mission(
        mission_id=mission.id,
        reflection=reflection,
    )
    print("    -> Mission marked complete in local SQLite database.")

    # 5. Mindful Progress Summary
    stats = storage.get_progress_summary()
    print("\n[5] Updated Local Progress Summary:")
    print(f"    - Completed Missions: {stats['completed_missions']}")
    print(f"    - Total Outdoor Minutes: {stats['total_outdoor_minutes']} min")
    print(f"    - Recent Reflections Count: {len(stats['recent_reflections'])}")
    if stats["recent_reflections"]:
        latest = stats["recent_reflections"][0]
        print(f"    - Latest Journal: \"{latest['reflection']}\"")

    print("\n" + "=" * 65)
    print("✨ Outdoor Demonstration Run Complete! All data saved locally.")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()
