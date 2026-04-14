"""
Stewie Windows API Utilities — ctypes wrappers for Win32 API calls.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

from loguru import logger


# ═══════════════════════════════════════════
# WINDOW MANAGEMENT
# ═══════════════════════════════════════════


def get_foreground_window_title() -> str:
    """Get the title of the currently focused window."""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def find_window_by_title(title_substring: str) -> Optional[int]:
    """
    Find a window handle by title substring.

    Args:
        title_substring: Partial window title to search for.

    Returns:
        Window handle (HWND), or None if not found.
    """
    result = []

    def enum_callback(hwnd, _):
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            if title_substring.lower() in buf.value.lower():
                result.append(hwnd)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
    )
    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

    return result[0] if result else None


def bring_window_to_front(hwnd: int) -> bool:
    """Bring a window to the foreground."""
    try:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════
# SYSTEM INFO
# ═══════════════════════════════════════════


def get_screen_resolution() -> tuple[int, int]:
    """Get the primary screen resolution."""
    width = ctypes.windll.user32.GetSystemMetrics(0)
    height = ctypes.windll.user32.GetSystemMetrics(1)
    return width, height


def get_battery_status() -> Optional[dict]:
    """Get battery status information."""
    try:

        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_byte),
                ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte),
                ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", wintypes.DWORD),
                ("BatteryFullLifeTime", wintypes.DWORD),
            ]

        status = SYSTEM_POWER_STATUS()
        ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))

        return {
            "plugged_in": status.ACLineStatus == 1,
            "percent": status.BatteryLifePercent,
            "seconds_remaining": (
                status.BatteryLifeTime
                if status.BatteryLifeTime != 0xFFFFFFFF
                else None
            ),
        }
    except Exception as e:
        logger.error(f"Failed to get battery status: {e}")
        return None


def is_admin() -> bool:
    """Check if the current process has admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
