"""Unit tests for TrailBuddy Local privacy enforcement and offline guarantees.

Verifies:
- Detection and rejection of external network URLs
- Verification of localhost-only Ollama endpoints
- Verification of zero-telemetry configuration
- Verification of local-only Streamlit configuration
"""

import pytest
import config
from src.privacy import (
    is_local_url,
    verify_ollama_endpoint,
    verify_privacy_posture,
    PrivacyViolationError,
)


def test_is_local_url():
    """Verify that only loopback addresses are accepted."""
    assert is_local_url("http://localhost:11434") is True
    assert is_local_url("http://127.0.0.1:11434") is True
    assert is_local_url("http://127.0.0.1:8501") is True
    assert is_local_url("http://[::1]:11434") is True

    # External addresses must return False
    assert is_local_url("https://api.openai.com/v1") is False
    assert is_local_url("http://192.168.1.50:11434") is False
    assert is_local_url("https://trailbuddy-cloud.com") is False
    assert is_local_url("https://analytics.google.com") is False


def test_verify_ollama_endpoint_blocks_remote():
    """Verify that non-local Ollama endpoints raise PrivacyViolationError."""
    assert verify_ollama_endpoint("http://127.0.0.1:11434") is True
    
    with pytest.raises(PrivacyViolationError) as exc:
        verify_ollama_endpoint("https://remote-llm.azure.com")
    assert "strictly offline-first" in str(exc.value)


def test_privacy_posture_compliance():
    """Verify that configuration strictly enforces privacy rules."""
    posture = verify_privacy_posture()
    assert posture["telemetry_disabled"] is True
    assert posture["external_network_blocked"] is True
    assert posture["gps_disabled"] is True
    assert posture["ollama_local_only"] is True
    assert posture["database_storage"] == "local_sqlite"
    assert posture["compliant"] is True


def test_default_config_binds_localhost():
    """Verify that default network host settings point to localhost."""
    assert config.STREAMLIT_HOST in ("127.0.0.1", "localhost")
    assert config.TELEMETRY_ENABLED is False
    assert config.ALLOW_EXTERNAL_CALLS is False
    assert config.ALLOW_GPS_COLLECTION is False
