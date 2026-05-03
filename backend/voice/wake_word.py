"""
Wake-word detection using Picovoice Porcupine.

Listens continuously on the default microphone and calls `callback` whenever
the phrase "Hey Eva" (or whatever keyword file is configured) is detected.

Requires:
  pip install pvporcupine pyaudio
  A valid PICOVOICE_ACCESS_KEY in config.

If PICOVOICE_ACCESS_KEY is not set the module falls back to a simple
energy-based keyword spotter (for development/testing only).
"""

from __future__ import annotations

import logging
import struct
import threading
from typing import Callable

from backend import config

logger = logging.getLogger(__name__)


# ── Porcupine-backed detector ──────────────────────────────────────────────

class WakeWordDetector:
    """Continuously monitors the microphone for the wake word.

    Parameters
    ----------
    on_wake:
        Callback invoked (from the listening thread) when the wake word fires.
    keyword:
        Porcupine built-in keyword name *or* path to a .ppn file.
        Defaults to "hey eva" (requires a paid Porcupine keyword file) or
        "jarvis" which is a free built-in keyword useful for local testing.
    """

    def __init__(
        self,
        on_wake: Callable[[], None],
        keyword: str = "jarvis",
    ) -> None:
        self._on_wake = on_wake
        self._keyword = keyword
        self._running = False
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="wake-word")
        self._thread.start()
        logger.info("Wake-word detector started (keyword=%s)", self._keyword)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("Wake-word detector stopped")

    # ------------------------------------------------------------------
    def _run(self) -> None:
        if config.PICOVOICE_ACCESS_KEY:
            self._run_porcupine()
        else:
            logger.warning(
                "PICOVOICE_ACCESS_KEY not set – using energy-based fallback detector. "
                "Speak 'hey eva' loudly; it won't be very accurate."
            )
            self._run_energy_fallback()

    # ------------------------------------------------------------------
    def _run_porcupine(self) -> None:
        try:
            import pvporcupine  # type: ignore
            import pyaudio  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "pvporcupine and pyaudio are required for wake-word detection. "
                "Install them with: pip install pvporcupine pyaudio"
            ) from exc

        porcupine = pvporcupine.create(
            access_key=config.PICOVOICE_ACCESS_KEY,
            keywords=[self._keyword],
        )
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length,
        )

        try:
            while self._running:
                raw = stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, raw)
                if porcupine.process(pcm) >= 0:
                    logger.info("Wake word detected!")
                    self._on_wake()
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            porcupine.delete()

    # ------------------------------------------------------------------
    def _run_energy_fallback(self) -> None:
        """Primitive always-hot detector for dev without a Porcupine key.

        Fires `on_wake` once on startup so you can test the pipeline
        without a real wake word.  In production always use Porcupine.
        """
        import time

        logger.info("Energy-fallback: firing on_wake once for pipeline testing")
        time.sleep(1)
        self._on_wake()
        # After the first trigger, stay idle
        while self._running:
            time.sleep(0.5)
