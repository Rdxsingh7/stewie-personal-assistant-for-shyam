"""
Stewie Application Manager — Open, close, and manage Windows applications.

Uses a configurable app registry and fallback discovery mechanisms.
"""

from __future__ import annotations

import getpass
import os
import subprocess
from pathlib import Path
from typing import Optional

import psutil
import yaml
from loguru import logger


# ═══════════════════════════════════════════
# APP REGISTRY
# ═══════════════════════════════════════════


def _load_app_registry() -> dict[str, dict]:
    """Load the app registry from YAML config."""
    registry_path = Path(__file__).parent.parent / "config" / "app_registry.yaml"

    if not registry_path.exists():
        logger.warning(f"App registry not found: {registry_path}")
        return {}

    with open(registry_path, "r") as f:
        data = yaml.safe_load(f)

    apps = data.get("apps", {})
    username = getpass.getuser()

    # Resolve {username} placeholders
    resolved = {}
    for name, info in apps.items():
        path = info.get("path", "").replace("{username}", username)
        aliases = info.get("aliases", [])
        resolved[name] = {"path": path, "aliases": aliases}

    return resolved


# Global registry — loaded once
APP_REGISTRY = _load_app_registry()


def _find_app_path(app_name: str) -> Optional[str]:
    """
    Find an application's executable path by name or alias.

    Checks:
    1. Direct match in registry
    2. Alias match in registry
    3. System PATH
    """
    app_lower = app_name.lower().strip()

    # 1. Direct match
    if app_lower in APP_REGISTRY:
        return APP_REGISTRY[app_lower]["path"]

    # 2. Alias match
    for name, info in APP_REGISTRY.items():
        if app_lower in [a.lower() for a in info.get("aliases", [])]:
            return info["path"]

    # 3. System PATH fallback
    return None


# ═══════════════════════════════════════════
# APPLICATION CONTROL
# ═══════════════════════════════════════════


async def open_application(app_name: str) -> str:
    """
    Launch a Windows application by its friendly name.

    Args:
        app_name: Name of the app (e.g., "Chrome", "Word", "Notepad").

    Returns:
        Confirmation message.
    """
    app_path = _find_app_path(app_name)

    try:
        if app_path:
            logger.info(f"Opening '{app_name}' from: {app_path}")

            if app_path.startswith("ms-"):
                # Windows protocol handler (e.g., ms-settings:)
                os.startfile(app_path)
            else:
                subprocess.Popen(
                    app_path,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        else:
            # Fallback: use the 'start' command
            logger.info(
                f"App '{app_name}' not in registry — "
                f"attempting system search."
            )
            subprocess.Popen(
                f'start "" "{app_name}"',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        return f"Opened {app_name}."

    except FileNotFoundError:
        error_msg = (
            f"Could not find '{app_name}'. "
            f"Please check if it's installed."
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    except Exception as e:
        logger.error(f"Failed to open '{app_name}': {e}")
        raise


async def close_application(app_name: str) -> str:
    """
    Gracefully terminate a running application by name.

    Args:
        app_name: Name of the application to close.

    Returns:
        Confirmation message.
    """
    app_lower = app_name.lower().strip()
    closed = False

    for proc in psutil.process_iter(["name", "pid"]):
        try:
            proc_name = proc.info["name"].lower()
            if app_lower in proc_name:
                proc.terminate()
                closed = True
                logger.info(
                    f"Terminated process: {proc.info['name']} "
                    f"(PID {proc.info['pid']})"
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if closed:
        return f"Closed {app_name}."
    else:
        logger.warning(f"No running process found for '{app_name}'")
        return f"No running instance of {app_name} was found."


async def list_running_apps() -> list[str]:
    """List currently running applications with visible windows."""
    apps = set()
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"]
            if name and not name.startswith("_"):
                apps.add(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(apps)


# ═══════════════════════════════════════════
# DICTATION / TYPING
# ═══════════════════════════════════════════


async def type_text(text: str, interval: float = 0.02, press_enter: bool = True) -> str:
    """
    Type text into the currently focused window.

    Uses pyautogui for cross-application compatibility.

    Args:
        text: The text to type.
        interval: Delay between keystrokes (seconds).
        press_enter: Whether to press the Enter key after typing. Defaults to True.

    Returns:
        Confirmation message.
    """
    import time
    import pyautogui

    # Brief pause to ensure focus
    time.sleep(0.5)

    try:
        # pyautogui.typewrite only works with ASCII
        # Use pyperclip + Ctrl+V for Unicode support
        if text.isascii():
            pyautogui.typewrite(text, interval=interval)
        else:
            import pyperclip

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")

        if press_enter:
            # Brief pause before pressing enter
            time.sleep(0.2)
            pyautogui.press("enter")

        logger.info(f"Typed {len(text)} characters (Enter pressed: {press_enter})")
        return f"Typed the text successfully."

    except Exception as e:
        logger.error(f"Failed to type text: {e}")
        raise
