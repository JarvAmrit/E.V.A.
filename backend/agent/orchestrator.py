"""
E.V.A. Agent Orchestrator using OpenAI function-calling.

Maintains a rolling conversation history and dispatches tool calls
as needed.  Each call to `chat(user_text, ws_send)` returns Eva's
text reply and may trigger one or more tool calls along the way.

ws_send is an optional async callable used to push real-time status
messages (tool calls, URLs) to the Electron frontend.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

import openai

from backend import config
from backend.agent import prompts
from backend.agent.tools import (
    browser,
    memory,
    system,
    web_search,
)

logger = logging.getLogger(__name__)

# ── OpenAI tool schema ─────────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": prompts.TOOL_DESCRIPTIONS["web_search"],
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results (default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browse_url",
            "description": prompts.TOOL_DESCRIPTIONS["browse_url"],
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to open"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_page",
            "description": prompts.TOOL_DESCRIPTIONS["summarize_page"],
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to summarise"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": prompts.TOOL_DESCRIPTIONS["run_command"],
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "Shell command to run"}
                },
                "required": ["cmd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": prompts.TOOL_DESCRIPTIONS["open_app"],
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "macOS app name"}
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_create",
            "description": prompts.TOOL_DESCRIPTIONS["calendar_create"],
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start": {"type": "string", "description": "ISO-8601 datetime"},
                    "end": {"type": "string", "description": "ISO-8601 datetime"},
                    "calendar": {"type": "string", "default": "Home"},
                    "notes": {"type": "string", "default": ""},
                },
                "required": ["title", "start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reminder_create",
            "description": prompts.TOOL_DESCRIPTIONS["reminder_create"],
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "due": {
                        "type": "string",
                        "description": "ISO-8601 due datetime (optional)",
                    },
                    "notes": {"type": "string", "default": ""},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_imessage",
            "description": prompts.TOOL_DESCRIPTIONS["send_message"],
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "Phone number or Apple ID",
                    },
                    "message": {"type": "string"},
                },
                "required": ["recipient", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_store",
            "description": prompts.TOOL_DESCRIPTIONS["memory_store"],
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_search",
            "description": prompts.TOOL_DESCRIPTIONS["memory_search"],
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "n_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_battery_level",
            "description": "Get the current macOS battery level.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the screen and save it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to save the screenshot (default /tmp/eva_screenshot.png)",
                        "default": "/tmp/eva_screenshot.png",
                    }
                },
            },
        },
    },
]

# ── Tool dispatch ──────────────────────────────────────────────────────────

def _dispatch_tool(name: str, args: dict, openai_client: openai.OpenAI) -> str:
    """Execute a tool call and return its string result."""
    if name == "web_search":
        results = web_search.web_search(**args)
        return json.dumps(results, ensure_ascii=False)
    if name == "browse_url":
        result = browser.browse_url(**args)
        return json.dumps({"text": result["text"], "url": result["url"]})
    if name == "summarize_page":
        return browser.summarize_page(args["url"], openai_client)
    if name == "run_command":
        return system.run_command(**args)
    if name == "open_app":
        return system.open_app(**args)
    if name == "calendar_create":
        return system.calendar_create(**args)
    if name == "reminder_create":
        return system.reminder_create(**args)
    if name == "send_imessage":
        return system.send_imessage(**args)
    if name == "memory_store":
        return memory.memory_store(**args)
    if name == "memory_search":
        results = memory.memory_search(**args)
        return json.dumps(results, ensure_ascii=False)
    if name == "get_battery_level":
        return system.get_battery_level()
    if name == "take_screenshot":
        return system.take_screenshot(**args)
    return f"Unknown tool: {name}"


# ── Orchestrator class ─────────────────────────────────────────────────────

class Orchestrator:
    """Stateful agent that maintains conversation history and dispatches tools.

    Parameters
    ----------
    ws_send:
        Optional async callable ``(dict) -> None`` used to push events to
        the Electron frontend over WebSocket.
    """

    MAX_HISTORY = 40  # Keep last N messages (to manage token budget)

    def __init__(self, ws_send: Optional[Callable] = None) -> None:
        self._ws_send = ws_send
        self._client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        self._history: list[dict] = []

    # ------------------------------------------------------------------
    def _push(self, event: dict) -> None:
        """Fire-and-forget push to the WebSocket frontend (if available)."""
        if self._ws_send:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                asyncio.ensure_future(self._ws_send(event), loop=loop)
            except RuntimeError:
                # No running loop (e.g. called from a sync thread) — skip push
                logger.debug("ws_send skipped: no running event loop")
            except Exception as exc:
                logger.debug("ws_send failed: %s", exc)

    # ------------------------------------------------------------------
    def chat(self, user_text: str) -> str:
        """Process a user utterance and return Eva's text reply.

        Handles multi-step tool calling internally.
        """
        self._history.append({"role": "user", "content": user_text})
        self._push({"type": "transcript", "role": "user", "text": user_text})

        messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}] + self._history[
            -self.MAX_HISTORY :
        ]

        # Agentic loop: keep calling the LLM until it produces a final reply
        for _ in range(10):  # max 10 tool rounds per turn
            response = self._client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                # Add assistant's tool-call message to history
                messages.append(msg.model_dump(exclude_unset=True))

                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info("Tool call: %s(%s)", tool_name, tool_args)
                    self._push(
                        {"type": "tool_call", "name": tool_name, "args": tool_args}
                    )

                    # If browsing a URL, tell the UI to load it
                    if tool_name in ("browse_url", "summarize_page") and "url" in tool_args:
                        self._push({"type": "load_url", "url": tool_args["url"]})

                    tool_result = _dispatch_tool(tool_name, tool_args, self._client)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_result,
                        }
                    )
            else:
                # Final text reply
                reply: str = (msg.content or "").strip()
                self._history.append({"role": "assistant", "content": reply})
                self._push({"type": "transcript", "role": "assistant", "text": reply})
                logger.info("Eva: %s", reply[:120])
                return reply

        return "I'm sorry sir, I seem to have gotten stuck in a loop. Please try again."
