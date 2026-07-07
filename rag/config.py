"""Environment-driven configuration for the RAG layer.

Reads a local .env file (simple KEY=VALUE lines, no dependency on python-dotenv)
and environment variables. Environment variables win over .env values.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_dotenv() -> dict[str, str]:
    values: dict[str, str] = {}
    if _ENV_FILE.exists():
        for line in _ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_DOTENV = _load_dotenv()


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, _DOTENV.get(key, default))


def env_int(key: str, default: int) -> int:
    try:
        return int(env(key, str(default)))
    except ValueError:
        return default


def env_float(key: str, default: float) -> float:
    try:
        return float(env(key, str(default)))
    except ValueError:
        return default


# Vector store / retrieval
VECTOR_DB_PATH = env("VECTOR_DB_PATH", "data/vector_store")
RAG_TOP_K_DFMEA = env_int("RAG_TOP_K_DFMEA", 5)
RAG_TOP_K_DVPR = env_int("RAG_TOP_K_DVPR", 5)
RAG_TOP_K_LESSONS = env_int("RAG_TOP_K_LESSONS", 3)
RAG_TOP_K_STANDARDS = env_int("RAG_TOP_K_STANDARDS", 3)
RAG_MIN_SIMILARITY = env_float("RAG_MIN_SIMILARITY", 0.30)
RAG_FORCE_FALLBACK_EMBEDDER = env("RAG_FORCE_FALLBACK_EMBEDDER", "") in ("1", "true", "yes")

# Optional LLM generation layer (off unless a provider is configured)
RAG_LLM_PROVIDER = env("RAG_LLM_PROVIDER", "").lower()  # "anthropic" | "openai" | ""
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", "claude-haiku-4-5")
OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = env("OPENAI_BASE_URL", "")  # for Azure/compatible gateways
LLM_MAX_TOKENS = env_int("LLM_MAX_TOKENS", 4000)
