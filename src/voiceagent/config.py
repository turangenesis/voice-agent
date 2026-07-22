"""Central config, all overridable via environment (op run injects these)."""

import os


def index() -> str:
    """Which Moss index to read/write. Read at call time so the CLI can set it."""
    return os.getenv("MOSS_INDEX", "docs")


def client_id() -> str | None:
    """Optional client scope within a shared index. None = no filter (whole index)."""
    return os.getenv("VOICEAGENT_CLIENT") or None


MODEL_ID = os.getenv("MOSS_MODEL_ID", "moss-minilm")

# Anthropic — only for the HTTP API's /ask answer composing (v3 Path B). Cheapest model by default.
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")


def has_anthropic_key() -> bool:
    """True once a real key is in place (placeholder 'PENDING' / empty counts as absent)."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key) and key != "PENDING"
CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# LiveKit Inference model choices (STT / LLM / TTS)
STT_MODEL = os.getenv("LIVEKIT_STT_MODEL", "deepgram/nova-3")
LLM_MODEL = os.getenv("LIVEKIT_LLM_MODEL", "openai/gpt-4.1-mini")
TTS_MODEL = os.getenv("LIVEKIT_TTS_MODEL", "cartesia/sonic-3")
TTS_VOICE = os.getenv("LIVEKIT_TTS_VOICE", "")
