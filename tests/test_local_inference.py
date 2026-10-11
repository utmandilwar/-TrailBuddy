"""Phase 1: Working local Ollama inference test.

Verifies:
1. Privacy boundary: Ollama endpoint must be localhost / 127.0.0.1.
2. Ollama connectivity: Local Ollama daemon is reachable.
3. Model availability: qwen2.5:3b is installed.
4. Inference execution: Generates a valid response using local CPU inference.
"""

import pytest
import config
from src.privacy import verify_ollama_endpoint, PrivacyViolationError, verify_privacy_posture
from src.llm import OllamaClient


def test_privacy_endpoint_guard():
    """Verify that remote endpoints are blocked by privacy rules."""
    assert verify_ollama_endpoint("http://127.0.0.1:11434") is True
    assert verify_ollama_endpoint("http://localhost:11434") is True
    
    with pytest.raises(PrivacyViolationError):
        verify_ollama_endpoint("https://api.openai.com/v1")

    with pytest.raises(PrivacyViolationError):
        verify_ollama_endpoint("http://remote-ollama.example.com:11434")


def test_privacy_posture():
    """Verify that telemetry and external network flags are strictly disabled."""
    posture = verify_privacy_posture()
    assert posture["telemetry_disabled"] is True
    assert posture["external_network_blocked"] is True
    assert posture["gps_disabled"] is True
    assert posture["ollama_local_only"] is True
    assert posture["compliant"] is True


def test_ollama_health_and_model():
    """Verify local Ollama service and presence of qwen2.5:3b."""
    client = OllamaClient()
    health = client.check_health()
    assert health["available"] is True, f"Ollama is not running: {health.get('error')}"
    assert health["target_model_installed"] is True, (
        f"Target model '{client.model}' not found in installed models: {health.get('models')}"
    )


def test_ollama_local_inference():
    """Verify that local inference completes successfully with JSON output."""
    client = OllamaClient()
    prompt = 'Return a JSON object with a single key "status" and value "ready".'
    response_text = client.generate(prompt=prompt, json_format=True)
    
    assert response_text is not None and len(response_text.strip()) > 0
    # Must contain valid JSON response
    import json
    parsed = json.loads(response_text)
    assert parsed.get("status") == "ready"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
