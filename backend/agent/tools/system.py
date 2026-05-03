"""
macOS system integration tools for E.V.A.

All macOS-specific calls go through AppleScript (via osascript) or
standard shell commands.  Each function returns a string result/status.

These tools only work on macOS.  On other platforms they raise
RuntimeError with a clear message.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

_SAFE_COMMANDS = frozenset(
    [
        "date",
        "uptime",
        "whoami",
        "sw_vers",
        "system_profiler",
        "pmset",
        "osascript",
        "open",
        "say",
        "screencapture",
        "ls",
        "pwd",
    ]
)


def _require_macos() -> None:
    if platform.system() != "Darwin":
        raise RuntimeError("This tool is only available on macOS.")


def _run_applescript(script: str) -> str:
    _require_macos()
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    output = (result.stdout + result.stderr).strip()
    logger.debug("AppleScript result: %r", output)
    return output


def run_command(cmd: str) -> str:
    """Run a safe shell command and return stdout + stderr.

    Only the first word (the binary name) is checked against an allowlist
    to prevent obvious misuse.  The command is passed as a list via shlex
    to avoid shell-injection risks.
    """
    import shlex

    _require_macos()
    parts = shlex.split(cmd) if cmd.strip() else []
    if not parts:
        return "Empty command."
    binary = parts[0]
    if binary not in _SAFE_COMMANDS:
        return f"Command '{binary}' is not in the allowlist. Blocked for safety."

    result = subprocess.run(parts, capture_output=True, text=True, timeout=15)
    return (result.stdout + result.stderr).strip()


def open_app(app_name: str) -> str:
    """Open a macOS application by name."""
    _require_macos()
    result = subprocess.run(
        ["open", "-a", app_name], capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        return f"Opened {app_name}."
    return f"Could not open '{app_name}': {result.stderr.strip()}"


def calendar_create(
    title: str,
    start: str,
    end: str,
    calendar: str = "Home",
    notes: str = "",
) -> str:
    """Create a calendar event via AppleScript.

    Parameters
    ----------
    title:    Event title.
    start:    ISO-8601 datetime string, e.g. "2025-07-04T09:00:00".
    end:      ISO-8601 datetime string.
    calendar: Calendar name (default "Home").
    notes:    Optional notes/description.
    """
    # AppleScript date literal format: "MM/DD/YYYY HH:MM:SS AM/PM"
    # We convert from ISO via Python's datetime
    from datetime import datetime

    fmt_in = "%Y-%m-%dT%H:%M:%S"
    fmt_as = "%m/%d/%Y %H:%M:%S"
    try:
        start_dt = datetime.fromisoformat(start).strftime(fmt_as)
        end_dt = datetime.fromisoformat(end).strftime(fmt_as)
    except ValueError:
        return "Invalid datetime format. Use ISO-8601, e.g. YYYY-MM-DDTHH:MM:SS"

    script = f"""
tell application "Calendar"
    tell calendar "{calendar}"
        set newEvent to make new event with properties ¬
            {{summary:"{title}", start date:date "{start_dt}", end date:date "{end_dt}", description:"{notes}"}}
    end tell
end tell
"""
    _run_applescript(script)
    return f"Event '{title}' created on {calendar} calendar from {start} to {end}."


def reminder_create(title: str, due: Optional[str] = None, notes: str = "") -> str:
    """Create a macOS Reminder via AppleScript."""
    due_clause = ""
    if due:
        from datetime import datetime

        fmt_as = "%m/%d/%Y %H:%M:%S"
        try:
            due_str = datetime.fromisoformat(due).strftime(fmt_as)
            due_clause = f'set due date of newReminder to date "{due_str}"'
        except ValueError:
            pass

    script = f"""
tell application "Reminders"
    set newReminder to make new reminder with properties {{name:"{title}", body:"{notes}"}}
    {due_clause}
end tell
"""
    _run_applescript(script)
    return f"Reminder '{title}' created."


def send_imessage(recipient: str, message: str) -> str:
    """Send an iMessage via AppleScript.

    Parameters
    ----------
    recipient: Phone number or Apple ID email.
    message:   Message text.
    """
    script = f"""
tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy "{recipient}" of targetService
    send "{message}" to targetBuddy
end tell
"""
    _run_applescript(script)
    return f"iMessage sent to {recipient}."


def get_battery_level() -> str:
    """Return current battery percentage."""
    result = subprocess.run(
        ["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5
    )
    return result.stdout.strip()


def take_screenshot(path: str = "/tmp/eva_screenshot.png") -> str:  # noqa: S108
    """Capture the screen and save to *path*."""
    result = subprocess.run(
        ["screencapture", "-x", path], capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        return f"Screenshot saved to {path}"
    return f"Screenshot failed: {result.stderr.strip()}"
