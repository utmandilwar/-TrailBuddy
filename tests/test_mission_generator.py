"""Unit and integration tests for MissionGenerator.

Uses unittest.mock to test unit generation and retry logic without calling external processes.
Includes an optional live Ollama integration test.
"""

import json
from unittest.mock import MagicMock
import pytest

from src.schemas import MissionRequest, Mission
from src.mission_generator import (
    MissionGenerator,
    MissionGenerationError,
    extract_json_payload,
)
from src.llm import OllamaClient, OllamaConnectionError


@pytest.fixture
def sample_request() -> MissionRequest:
    return MissionRequest(
        duration_minutes=20,
        interest="nature",
        difficulty="easy",
        environment="park",
        accessibility="Wheelchair accessible flat paths",
    )


@pytest.fixture
def valid_mission_dict() -> dict:
    return {
        "title": "Accessible Park Flora Tour",
        "description": "A mindful 20-minute loop along paved park trails.",
        "duration_minutes": 20,
        "tasks": [
            "Follow the paved perimeter trail at a calm pace.",
            "Notice the changing bark textures on three mature trees.",
            "Pause on a park bench and close your eyes for 60 seconds of listening.",
        ],
        "required_items": ["Water bottle"],
        "safety_reminders": ["Stay on paved paths", "Keep hydrated"],
        "reflection_question": "What sound was most distant?",
    }


def test_extract_json_payload_clean():
    """Verify clean JSON string extraction."""
    raw = '{"title": "Test Walk", "tasks": []}'
    parsed = extract_json_payload(raw)
    assert parsed["title"] == "Test Walk"


def test_extract_json_payload_markdown_fence():
    """Verify JSON extraction when enclosed in markdown fences."""
    raw = 'Here is your mission:\n```json\n{"title": "Fenced Walk", "duration_minutes": 10}\n```\nEnjoy outdoors!'
    parsed = extract_json_payload(raw)
    assert parsed["title"] == "Fenced Walk"
    assert parsed["duration_minutes"] == 10


def test_extract_json_payload_invalid():
    """Verify that malformed JSON raises JSONDecodeError."""
    with pytest.raises(json.JSONDecodeError):
        extract_json_payload("Sorry, I cannot help with that without outdoor details.")


def test_generate_mission_success_first_attempt(sample_request, valid_mission_dict):
    """Verify successful generation on the first model attempt."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = json.dumps(valid_mission_dict)

    generator = MissionGenerator(llm_client=mock_client)
    mission = generator.generate_mission(sample_request)

    assert isinstance(mission, Mission)
    assert mission.title == "Accessible Park Flora Tour"
    assert mission.duration_minutes == 20
    assert len(mission.tasks) == 3
    assert mock_client.generate.call_count == 1


def test_generate_mission_retries_on_malformed_json(sample_request, valid_mission_dict):
    """Verify that a malformed first response triggers a retry and succeeds on attempt 2."""
    mock_client = MagicMock(spec=OllamaClient)
    # First attempt: invalid truncated JSON; Second attempt: valid JSON
    mock_client.generate.side_effect = [
        "Here is your mission: { title: truncated",
        json.dumps(valid_mission_dict),
    ]

    generator = MissionGenerator(llm_client=mock_client)
    mission = generator.generate_mission(sample_request)

    assert isinstance(mission, Mission)
    assert mission.title == "Accessible Park Flora Tour"
    assert mock_client.generate.call_count == 2


def test_generate_mission_retries_on_missing_fields(sample_request, valid_mission_dict):
    """Verify that missing mandatory fields on attempt 1 trigger a retry."""
    mock_client = MagicMock(spec=OllamaClient)
    # Attempt 1: missing tasks; Attempt 2: valid
    invalid_dict = {"title": "Only a title", "duration_minutes": 20}
    mock_client.generate.side_effect = [
        json.dumps(invalid_dict),
        json.dumps(valid_mission_dict),
    ]

    generator = MissionGenerator(llm_client=mock_client)
    mission = generator.generate_mission(sample_request)

    assert isinstance(mission, Mission)
    assert mock_client.generate.call_count == 2


def test_generate_mission_fails_after_retries(sample_request):
    """Verify that consecutive invalid outputs raise MissionGenerationError."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.side_effect = [
        "Bad output 1",
        "Bad output 2",
    ]

    generator = MissionGenerator(llm_client=mock_client)
    with pytest.raises(MissionGenerationError) as exc:
        generator.generate_mission(sample_request)
    assert "Unable to generate a valid mission after retry" in str(exc.value)
    assert mock_client.generate.call_count == 2


def test_model_unavailable_raises_connection_error(sample_request):
    """Verify that Ollama connection errors are propagated directly."""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.side_effect = OllamaConnectionError(
        "Could not connect to Ollama at http://127.0.0.1:11434"
    )

    generator = MissionGenerator(llm_client=mock_client)
    with pytest.raises(OllamaConnectionError):
        generator.generate_mission(sample_request)


@pytest.mark.integration
def test_real_ollama_mission_generation(sample_request):
    """Integration test against actual running local Ollama instance."""
    real_client = OllamaClient()
    health = real_client.check_health()
    if not health.get("available") or not health.get("target_model_installed"):
        pytest.skip("Local Ollama service or target model is not available for integration test.")

    generator = MissionGenerator(llm_client=real_client)
    mission = generator.generate_mission(sample_request)

    assert isinstance(mission, Mission)
    assert len(mission.title) >= 3
    assert mission.duration_minutes == 20
    assert 3 <= len(mission.tasks) <= 5
    assert len(mission.safety_reminders) >= 1
