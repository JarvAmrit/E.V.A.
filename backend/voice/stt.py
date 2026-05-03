"""
Speech-to-text using OpenAI Whisper (runs locally).

Records audio from the microphone until a period of silence, then
transcribes the recording and returns the text.

Requires:
  pip install openai-whisper sounddevice numpy
"""

from __future__ import annotations

import io
import logging
import time
import wave
from typing import Optional

import numpy as np

from backend import config

logger = logging.getLogger(__name__)

_model = None  # Lazy-loaded Whisper model


def _get_model():
    global _model
    if _model is None:
        import whisper  # type: ignore

        logger.info("Loading Whisper model '%s' …", config.WHISPER_MODEL)
        _model = whisper.load_model(config.WHISPER_MODEL)
        logger.info("Whisper model loaded")
    return _model


def record_until_silence(
    sample_rate: int = config.AUDIO_SAMPLE_RATE,
    silence_threshold: float = config.SILENCE_THRESHOLD,
    silence_duration: float = config.SILENCE_DURATION,
    max_duration: float = 30.0,
) -> np.ndarray:
    """Record microphone audio until silence is detected.

    Returns a float32 numpy array of audio samples (mono, 16 kHz).
    """
    try:
        import sounddevice as sd  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "sounddevice is required for microphone recording. "
            "Install with: pip install sounddevice"
        ) from exc

    chunk = int(sample_rate * 0.1)  # 100 ms chunks
    frames: list[np.ndarray] = []
    silent_chunks = 0
    required_silent_chunks = int(silence_duration / 0.1)
    max_chunks = int(max_duration / 0.1)

    logger.info("Recording … (speak now)")
    with sd.InputStream(
        samplerate=sample_rate,
        channels=config.AUDIO_CHANNELS,
        dtype="float32",
        blocksize=chunk,
    ) as stream:
        for _ in range(max_chunks):
            data, _ = stream.read(chunk)
            frames.append(data.flatten())
            rms = float(np.sqrt(np.mean(data**2)))
            if rms < silence_threshold:
                silent_chunks += 1
                if silent_chunks >= required_silent_chunks and len(frames) > required_silent_chunks:
                    break
            else:
                silent_chunks = 0

    audio = np.concatenate(frames)
    logger.info("Recording finished (%.2f s)", len(audio) / sample_rate)
    return audio


def transcribe(audio: np.ndarray) -> str:
    """Transcribe a float32 numpy audio array to text using Whisper."""
    model = _get_model()
    result = model.transcribe(audio, fp16=False, language="en")
    text: str = result.get("text", "").strip()
    logger.info("Transcribed: %r", text)
    return text


def record_and_transcribe() -> str:
    """Convenience helper: record then immediately transcribe."""
    audio = record_until_silence()
    return transcribe(audio)
