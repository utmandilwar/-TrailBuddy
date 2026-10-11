"""Configuration settings for TrailBuddy Local.

Follows privacy-first, offline-first design principles:
- Local Ollama inference at 127.0.0.1:11434
- No cloud AI fallbacks
- Local SQLite persistence
- Localhost only Streamlit binding
"""

import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "trailbuddy.db"

# Ollama Configuration
# Explicitly use 127.0.0.1 to avoid Windows IPv6 localhost resolution delays
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("TRAILBUDDY_MODEL", "qwen2.5:3b")

# Inference options
# num_gpu = 0 guarantees stable, fast CPU execution across all Windows hardware,
# preventing CUDA shared library overrun crashes on legacy/mobile GPUs.
DEFAULT_NUM_GPU = int(os.getenv("TRAILBUDDY_NUM_GPU", "0"))
INFERENCE_TIMEOUT_SECONDS = int(os.getenv("TRAILBUDDY_TIMEOUT", "60"))
MAX_RETRIES = 1

# Streamlit Local Server Defaults
STREAMLIT_HOST = "127.0.0.1"
STREAMLIT_PORT = 8501

# Privacy flags
TELEMETRY_ENABLED = False
ALLOW_EXTERNAL_CALLS = False
ALLOW_GPS_COLLECTION = False
