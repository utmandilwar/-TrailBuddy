"""Unit tests for TrailBuddy Local SQLite storage layer.

Verifies:
- Table initialization
- Mission persistence and retrieval
- Mission completion workflow and journal entry creation
- Non-gamified progress calculation
- Safe handling of missing records
"""

import tempfile
from pathlib import Path
import pytest

from src.schemas import Mission
from src.storage import StorageManager


@pytest.fixture
def temp_storage():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db_path = f.name
    
    storage = StorageManager(db_path=temp_db_path)
    yield storage
    
    # Cleanup
    try:
        Path(temp_db_path).unlink(missing_ok=True)
    except Exception:
        pass


@pytest.fixture
def sample_mission() -> Mission:
    return Mission(
        id="test-mission-123",
        title="Mindful Garden Stroll",
        description="A peaceful pause to connect with neighborhood flora.",
        duration_minutes=15,
        tasks=[
            "Find three shades of green among garden leaves.",
            "Listen for five distinct ambient outdoor sounds.",
            "Breathe deeply while noticing the air temperature.",
        ],
        required_items=["Water bottle"],
        safety_reminders=["Stay on paths", "Do not touch unknown plants"],
        reflection_question="What shade of green stood out most?",
    )


def test_init_and_save_mission(temp_storage, sample_mission):
    """Verify that missions can be saved and retrieved accurately."""
    temp_storage.save_mission(sample_mission)
    retrieved = temp_storage.get_mission(sample_mission.id)

    assert retrieved is not None
    assert retrieved.id == sample_mission.id
    assert retrieved.title == "Mindful Garden Stroll"
    assert retrieved.duration_minutes == 15
    assert len(retrieved.tasks) == 3
    assert retrieved.completed is False


def test_get_nonexistent_mission(temp_storage):
    """Verify that querying a missing mission returns None."""
    assert temp_storage.get_mission("does-not-exist") is None


def test_complete_mission_and_journal_creation(temp_storage, sample_mission):
    """Verify that completing a mission updates the mission and creates a journal entry."""
    temp_storage.save_mission(sample_mission)
    
    reflection_text = "I felt calm and heard a robin chirping near the fence."
    completed_mission = temp_storage.complete_mission(
        mission_id=sample_mission.id,
        reflection=reflection_text,
        date_completed="2026-10-11T10:00:00",
    )

    assert completed_mission is not None
    assert completed_mission.completed is True
    assert completed_mission.user_reflection == reflection_text
    assert completed_mission.completed_at == "2026-10-11T10:00:00"

    # Verify journal entry exists
    journals = temp_storage.list_journal_entries()
    assert len(journals) == 1
    assert journals[0].mission_id == sample_mission.id
    assert journals[0].reflection == reflection_text
    assert journals[0].duration_minutes == 15


def test_progress_summary(temp_storage, sample_mission):
    """Verify accurate calculation of outdoor minutes and completed count."""
    # Empty progress check
    initial_stats = temp_storage.get_progress_summary()
    assert initial_stats["completed_missions"] == 0
    assert initial_stats["total_outdoor_minutes"] == 0
    assert len(initial_stats["recent_reflections"]) == 0

    # Add and complete first mission (15 min)
    temp_storage.save_mission(sample_mission)
    temp_storage.complete_mission(
        mission_id=sample_mission.id,
        reflection="Reflected on morning calm.",
        date_completed="2026-10-11T10:00:00",
    )

    # Add and complete second mission (25 min)
    mission_2 = Mission(
        id="test-mission-456",
        title="Neighborhood Canopy Walk",
        description="Looking up at tree crowns.",
        duration_minutes=25,
        tasks=["Look up", "Notice leaf silhouettes", "Find a quiet bench"],
        safety_reminders=["Watch for traffic on crosswalks"],
    )
    temp_storage.save_mission(mission_2)
    temp_storage.complete_mission(
        mission_id=mission_2.id,
        reflection="The sycamore trees were majestic.",
        date_completed="2026-10-11T11:00:00",
    )

    # Check updated stats
    stats = temp_storage.get_progress_summary()
    assert stats["completed_missions"] == 2
    assert stats["total_outdoor_minutes"] == 40  # 15 + 25
    assert len(stats["recent_reflections"]) == 2
    assert stats["recent_reflections"][0]["title"] == "Neighborhood Canopy Walk"
