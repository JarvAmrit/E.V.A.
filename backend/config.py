"""
E.V.A. Configuration
All API keys and settings are loaded from environment variables or a .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


# ── OpenAI ─────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o")

# ── ElevenLabs (optional TTS) ──────────────────────────────────────────────
ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID: str = os.environ.get("ELEVENLABS_VOICE_ID", "")

# ── Picovoice / Porcupine (wake word) ─────────────────────────────────────
PICOVOICE_ACCESS_KEY: str = os.environ.get("PICOVOICE_ACCESS_KEY", "")

# ── Bing Search (optional – falls back to DuckDuckGo) ─────────────────────
BING_SEARCH_API_KEY: str = os.environ.get("BING_SEARCH_API_KEY", "")

# ── WebSocket server ──────────────────────────────────────────────────────
WS_HOST: str = os.environ.get("WS_HOST", "localhost")
WS_PORT: int = int(os.environ.get("WS_PORT", "8765"))

# ── Whisper STT ───────────────────────────────────────────────────────────
WHISPER_MODEL: str = os.environ.get("WHISPER_MODEL", "base.en")

# ── ChromaDB ──────────────────────────────────────────────────────────────
CHROMA_PERSIST_DIR: str = os.environ.get(
    "CHROMA_PERSIST_DIR",
    str(Path(__file__).resolve().parent.parent / "data" / "chroma"),
)

# ── TTS backend: "pyttsx3" or "elevenlabs" ────────────────────────────────
TTS_BACKEND: str = os.environ.get("TTS_BACKEND", "pyttsx3")

# ── Audio recording settings ─────────────────────────────────────────────
AUDIO_SAMPLE_RATE: int = 16000
AUDIO_CHANNELS: int = 1
SILENCE_THRESHOLD: float = float(os.environ.get("SILENCE_THRESHOLD", "0.01"))
SILENCE_DURATION: float = float(os.environ.get("SILENCE_DURATION", "1.5"))
