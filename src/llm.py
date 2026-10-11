"""Local Ollama client for TrailBuddy Local.

Provides robust, privacy-respecting local inference with zero cloud fallback.
Enforces local-only network endpoints and structured JSON output.
"""

import json
import logging
from typing import Any, Dict, Optional
import requests

import config
from src.privacy import verify_ollama_endpoint, PrivacyViolationError

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama interactions."""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when the Ollama service is unreachable."""
    pass


class OllamaModelNotFoundError(OllamaError):
    """Raised when the requested model is not downloaded locally."""
    pass


class OllamaInferenceError(OllamaError):
    """Raised when inference fails or returns an error."""
    pass


class OllamaClient:
    """Client for local Ollama inference service."""

    def __init__(
        self,
        base_url: str = config.OLLAMA_BASE_URL,
        model: str = config.DEFAULT_MODEL,
        num_gpu: int = config.DEFAULT_NUM_GPU,
        timeout: int = config.INFERENCE_TIMEOUT_SECONDS,
    ):
        # Enforce strict local endpoint verification
        verify_ollama_endpoint(base_url)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.num_gpu = num_gpu
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        """Check the status of the local Ollama instance and model availability."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                return {
                    "available": False,
                    "error": f"Ollama returned status code {resp.status_code}",
                    "models": [],
                    "target_model_installed": False,
                }
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            # Match model name either exact (qwen2.5:3b) or base name (qwen2.5:3b:latest)
            has_target = any(
                self.model == m or m.startswith(f"{self.model}:") or self.model.startswith(m)
                for m in models
            )
            return {
                "available": True,
                "error": None,
                "models": models,
                "target_model_installed": has_target,
            }
        except requests.exceptions.RequestException as e:
            return {
                "available": False,
                "error": (
                    f"Cannot connect to local Ollama service at {self.base_url}. "
                    "Make sure Ollama is running (`ollama serve`). "
                    f"Details: {str(e)}"
                ),
                "models": [],
                "target_model_installed": False,
            }

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_format: bool = True,
        temperature: float = 0.4,
    ) -> str:
        """Execute a local completion against Ollama.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            json_format: If True, constrains model output to JSON
            temperature: Sampling temperature (lower = more grounded)
            
        Returns:
            The raw text response from the model.
            
        Raises:
            OllamaConnectionError: If Ollama is unreachable.
            OllamaInferenceError: If Ollama returns an error or malformed payload.
        """
        verify_ollama_endpoint(self.base_url)
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_gpu": self.num_gpu,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        if json_format:
            payload["format"] = "json"

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectionError as e:
            raise OllamaConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Please verify that Ollama is running (`ollama serve`)."
            ) from e
        except requests.exceptions.Timeout as e:
            raise OllamaInferenceError(
                f"Inference request timed out after {self.timeout} seconds. "
                "Try a shorter duration or check system CPU load."
            ) from e
        except requests.exceptions.RequestException as e:
            raise OllamaInferenceError(f"HTTP request to Ollama failed: {e}") from e

        if response.status_code == 404:
            raise OllamaModelNotFoundError(
                f"Model '{self.model}' was not found in your local Ollama library. "
                f"Please run `ollama pull {self.model}` in your terminal."
            )
        elif response.status_code != 200:
            raise OllamaInferenceError(
                f"Ollama returned error {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
            return data.get("response", "")
        except json.JSONDecodeError as e:
            raise OllamaInferenceError(f"Invalid JSON response from Ollama server: {e}") from e
