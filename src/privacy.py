"""Privacy verification and enforcement module for TrailBuddy Local.

Enforces zero telemetry, offline-first execution, and localhost-only network traffic.
"""

from typing import Dict, Any
from urllib.parse import urlparse
import config


class PrivacyViolationError(Exception):
    """Raised when an operation violates local privacy constraints."""
    pass


def is_local_url(url: str) -> bool:
    """Check if the provided URL is strictly local (localhost or 127.0.0.1)."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return hostname in ("localhost", "127.0.0.1", "::1")


def verify_ollama_endpoint(endpoint_url: str = config.OLLAMA_BASE_URL) -> bool:
    """Verify that the Ollama endpoint points to a local address.
    
    Raises:
        PrivacyViolationError: If endpoint targets a non-local address.
    """
    if not is_local_url(endpoint_url):
        raise PrivacyViolationError(
            f"Non-local AI endpoint detected: '{endpoint_url}'. "
            "TrailBuddy Local is strictly offline-first and forbids cloud AI endpoints."
        )
    return True


def verify_privacy_posture() -> Dict[str, Any]:
    """Audit current application privacy posture.
    
    Returns a dictionary summarizing compliance with zero-telemetry and
    local-only operation rules.
    """
    ollama_local = is_local_url(config.OLLAMA_BASE_URL)
    
    return {
        "telemetry_disabled": not config.TELEMETRY_ENABLED,
        "external_network_blocked": not config.ALLOW_EXTERNAL_CALLS,
        "gps_disabled": not config.ALLOW_GPS_COLLECTION,
        "ollama_local_only": ollama_local,
        "database_storage": "local_sqlite",
        "compliant": (
            not config.TELEMETRY_ENABLED
            and not config.ALLOW_EXTERNAL_CALLS
            and not config.ALLOW_GPS_COLLECTION
            and ollama_local
        )
    }
