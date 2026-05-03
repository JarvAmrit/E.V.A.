"""
Text-to-speech output for E.V.A.

Supports two backends, selected by config.TTS_BACKEND:
  "pyttsx3"    – local, no API key needed
  "elevenlabs" – high-quality cloud TTS (requires ELEVENLABS_API_KEY)

Public API
----------
speak(text)  →  None   (plays audio synchronously)
"""

from __future__ import annotations

import logging

from backend import config

logger = logging.getLogger(__name__)


# ── pyttsx3 backend ────────────────────────────────────────────────────────

def _speak_pyttsx3(text: str) -> None:
    try:
        import pyttsx3  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pyttsx3 is required for local TTS. Install with: pip install pyttsx3"
        ) from exc

    engine = pyttsx3.init()
    # Use a slightly lower rate for a calmer, Jarvis-like cadence
    engine.setProperty("rate", 175)
    engine.say(text)
    engine.runAndWait()


# ── ElevenLabs backend ────────────────────────────────────────────────────

def _speak_elevenlabs(text: str) -> None:
    if not config.ELEVENLABS_API_KEY:
        logger.warning("ELEVENLABS_API_KEY not set – falling back to pyttsx3")
        _speak_pyttsx3(text)
        return

    try:
        from elevenlabs import generate, play, set_api_key  # type: ignore

        set_api_key(config.ELEVENLABS_API_KEY)
        voice_id = config.ELEVENLABS_VOICE_ID or "Rachel"
        audio = generate(text=text, voice=voice_id, model="eleven_monolingual_v1")
        play(audio)
    except ImportError as exc:
        raise RuntimeError(
            "elevenlabs package is required. Install with: pip install elevenlabs"
        ) from exc


# ── Public entry point ────────────────────────────────────────────────────

def speak(text: str) -> None:
    """Speak *text* aloud using the configured TTS backend."""
    if not text:
        return
    logger.info("TTS [%s]: %r", config.TTS_BACKEND, text[:80])
    if config.TTS_BACKEND == "elevenlabs":
        _speak_elevenlabs(text)
    else:
        _speak_pyttsx3(text)
