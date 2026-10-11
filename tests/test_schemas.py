"""Unit tests for TrailBuddy Local Pydantic schemas.

Verifies:
- Valid mission creation
- Missing mandatory fields
- Invalid durations
- Task count bounds (3 to 5 tasks)
- MissionRequest input validation
- JournalEntry schemas
"""

import pytest
from pydantic import ValidationError
from src.schemas import Mission, MissionRequest, JournalEntry


def test_valid_mission():
    """Verify that a compliant dictionary instantiates a Mission."""
    data = {
        "title": "Garden Leaf Safari",
        "description": "Spend 10 mindful minutes noticing leaf textures and vein patterns.",
        "duration_minutes": 10,
        "tasks": [
            "Find three different types of leaves without picking them.",
            "Notice the patterns and symmetry in their veins.",
            "Touch the texture of a dry leaf on the ground.",
        ],
        "required_items": ["Water bottle"],
        "safety_reminders": ["Stay on clear paths", "Do not touch unknown thorns or fungi"],
        "reflection_question": "Which leaf pattern felt most surprising?",
    }
    mission = Mission(**data)
    assert mission.title == "Garden Leaf Safari"
    assert mission.duration_minutes == 10
    assert len(mission.tasks) == 3
    assert mission.completed is False
    assert mission.id is not None


def test_missing_mandatory_fields():
    """Verify that omitting mandatory fields raises ValidationError."""
    # Missing tasks and safety_reminders
    with pytest.raises(ValidationError) as exc:
        Mission(
            title="Short Walk",
            description="A quick stroll around the block.",
            duration_minutes=10,
            tasks=[],  # Empty tasks
            safety_reminders=[],
        )
    errors = str(exc.value)
    assert "tasks" in errors or "safety_reminders" in errors


def test_invalid_duration():
    """Verify that negative, zero, or excessive durations are rejected."""
    valid_tasks = ["Observe sky", "Listen for birds", "Feel the ground"]
    valid_safety = ["Stay alert"]

    with pytest.raises(ValidationError):
        Mission(
            title="Zero Duration Walk",
            description="A brief mindfulness pause.",
            duration_minutes=0,
            tasks=valid_tasks,
            safety_reminders=valid_safety,
        )

    with pytest.raises(ValidationError):
        Mission(
            title="Negative Duration Walk",
            description="A brief mindfulness pause.",
            duration_minutes=-15,
            tasks=valid_tasks,
            safety_reminders=valid_safety,
        )

    with pytest.raises(ValidationError):
        Mission(
            title="Excessive Walk",
            description="A brief mindfulness pause.",
            duration_minutes=300,  # Max allowed is 120
            tasks=valid_tasks,
            safety_reminders=valid_safety,
        )


def test_task_count_boundaries():
    """Verify that missions must have between 3 and 5 actionable tasks."""
    safety = ["Watch footing"]
    
    # 2 tasks (too few)
    with pytest.raises(ValidationError):
        Mission(
            title="Under-tasked",
            description="Not enough tasks provided.",
            duration_minutes=10,
            tasks=["Task one", "Task two"],
            safety_reminders=safety,
        )

    # 6 tasks (too many)
    with pytest.raises(ValidationError):
        Mission(
            title="Over-tasked",
            description="Too many tasks provided.",
            duration_minutes=30,
            tasks=[
                "Task 1",
                "Task 2",
                "Task 3",
                "Task 4",
                "Task 5",
                "Task 6",
            ],
            safety_reminders=safety,
        )

    # Exactly 4 tasks (valid)
    mission_4 = Mission(
        title="Four Steps",
        description="A great four-step mission.",
        duration_minutes=20,
        tasks=["Task 1", "Task 2", "Task 3", "Task 4"],
        safety_reminders=safety,
    )
    assert len(mission_4.tasks) == 4


def test_mission_request_validation():
    """Verify that MissionRequest validates allowed inputs and rejects invalid ones."""
    # Valid request
    req = MissionRequest(
        duration_minutes=20,
        interest="nature",
        difficulty="easy",
        environment="park",
        accessibility="Paved flat paths only",
    )
    assert req.duration_minutes == 20
    assert req.interest == "nature"

    # Disallowed duration (e.g. 45 min)
    with pytest.raises(ValidationError):
        MissionRequest(
            duration_minutes=45,
            interest="nature",
            difficulty="easy",
            environment="park",
        )

    # Disallowed interest
    with pytest.raises(ValidationError):
        MissionRequest(
            duration_minutes=20,
            interest="extreme sports",
            difficulty="easy",
            environment="park",
        )

    # Disallowed environment
    with pytest.raises(ValidationError):
        MissionRequest(
            duration_minutes=20,
            interest="plants",
            difficulty="easy",
            environment="highway median",
        )


def test_journal_entry_schema():
    """Verify JournalEntry schema validation."""
    entry = JournalEntry(
        mission_id="12345",
        mission_title="Morning Bird Watch",
        date_completed="2026-10-11T09:00:00",
        duration_minutes=15,
        reflection="Heard 3 distinct songbirds near the oak tree.",
    )
    assert entry.completed is True
    assert entry.duration_minutes == 15
    assert "songbirds" in entry.reflection
