"""
E.V.A. Backend Entry Point

Starts:
  1. WebSocket server (localhost:8765) to communicate with the Electron frontend
  2. Wake-word detector
  3. Voice pipeline: STT → Agent → TTS

Usage:
  python -m backend.main
  # or from project root:
  python backend/main.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol

from backend import config
from backend.agent.orchestrator import Orchestrator
from backend.voice.stt import record_and_transcribe
from backend.voice.tts import speak
from backend.voice.wake_word import WakeWordDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("eva.main")

# ── Global state ──────────────────────────────────────────────────────────

connected_clients: Set[WebSocketServerProtocol] = set()
orchestrator: Optional[Orchestrator] = None
_listening = False  # True while recording user speech


async def broadcast(event: dict) -> None:
    """Send a JSON event to all connected WebSocket clients."""
    if not connected_clients:
        return
    payload = json.dumps(event)
    await asyncio.gather(
        *[ws.send(payload) for ws in connected_clients],
        return_exceptions=True,
    )


# ── Voice pipeline ────────────────────────────────────────────────────────

def _voice_pipeline() -> None:
    """Blocking: called in a background thread after the wake word fires."""
    global _listening

    _listening = True
    loop = asyncio.new_event_loop()

    try:
        # Notify frontend
        loop.run_until_complete(broadcast({"type": "state", "value": "listening"}))

        # STT
        user_text = record_and_transcribe()
        if not user_text:
            loop.run_until_complete(broadcast({"type": "state", "value": "idle"}))
            return

        # Agent
        loop.run_until_complete(broadcast({"type": "state", "value": "thinking"}))
        reply = orchestrator.chat(user_text)

        # TTS
        loop.run_until_complete(broadcast({"type": "state", "value": "speaking"}))
        speak(reply)
    finally:
        _listening = False
        loop.run_until_complete(broadcast({"type": "state", "value": "idle"}))
        loop.close()


def _on_wake() -> None:
    """Called by the wake-word detector; starts the voice pipeline in a thread."""
    if _listening:
        logger.info("Already listening – ignoring wake word")
        return
    logger.info("Wake word detected – starting voice pipeline")
    t = threading.Thread(target=_voice_pipeline, daemon=True, name="voice-pipeline")
    t.start()


# ── WebSocket server ──────────────────────────────────────────────────────

async def _ws_handler(ws: WebSocketServerProtocol) -> None:
    """Handle a single WebSocket connection from the Electron frontend."""
    connected_clients.add(ws)
    remote = ws.remote_address
    logger.info("Frontend connected: %s", remote)
    await ws.send(json.dumps({"type": "state", "value": "idle"}))

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "text_input":
                # Frontend sent a typed command (text override)
                text = msg.get("text", "").strip()
                if text and orchestrator:
                    await broadcast({"type": "state", "value": "thinking"})
                    reply = await asyncio.to_thread(orchestrator.chat, text)
                    await broadcast({"type": "state", "value": "speaking"})
                    await asyncio.to_thread(speak, reply)
                    await broadcast({"type": "state", "value": "idle"})

            elif msg_type == "ping":
                await ws.send(json.dumps({"type": "pong"}))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(ws)
        logger.info("Frontend disconnected: %s", remote)


# ── Main ──────────────────────────────────────────────────────────────────

async def _main() -> None:
    global orchestrator

    # Build ws_send callable that posts to the broadcast queue
    async def ws_send(event: dict) -> None:
        await broadcast(event)

    orchestrator = Orchestrator(ws_send=ws_send)
    logger.info("Orchestrator ready (model=%s)", config.OPENAI_MODEL)

    # Start wake-word detector
    detector = WakeWordDetector(on_wake=_on_wake)
    detector.start()

    # Greet on startup
    greeting = "E.V.A. online. All systems nominal. How can I assist you today?"
    logger.info(greeting)
    speak(greeting)

    # Start WebSocket server
    async with websockets.serve(_ws_handler, config.WS_HOST, config.WS_PORT):
        logger.info(
            "WebSocket server listening on ws://%s:%s", config.WS_HOST, config.WS_PORT
        )
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(_main())
