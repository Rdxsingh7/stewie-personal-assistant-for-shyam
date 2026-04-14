"""
Stewie System Controller — Brightness, volume, and power management.

Provides async interfaces to Windows system controls using native APIs.
"""

from __future__ import annotations

import ctypes
import subprocess

from loguru import logger


# ═══════════════════════════════════════════
# BRIGHTNESS CONTROL
# ═══════════════════════════════════════════


async def set_brightness(level: int) -> str:
    """
    Set screen brightness to a specific level.

    Args:
        level: Brightness level from 0 to 100.

    Returns:
        Confirmation message.
    """
    level = max(0, min(100, level))

    try:
        import screen_brightness_control as sbc

        sbc.set_brightness(level)
        logger.info(f"Brightness set to {level}%")
        return f"Brightness set to {level}%."
    except ImportError:
        # Fallback: use PowerShell/WMI
        return await _set_brightness_wmi(level)
    except Exception as e:
        logger.error(f"Failed to set brightness: {e}")
        raise


async def adjust_brightness(delta: int) -> str:
    """
    Adjust brightness by a relative amount.

    Args:
        delta: Amount to change. Positive = brighter, negative = dimmer.

    Returns:
        Confirmation message.
    """
    try:
        import screen_brightness_control as sbc

        current = sbc.get_brightness()[0]
        new_level = max(0, min(100, current + delta))
        sbc.set_brightness(new_level)
        logger.info(f"Brightness adjusted by {delta}: {current} → {new_level}")
        return f"Brightness adjusted to {new_level}%."
    except ImportError:
        logger.warning("screen_brightness_control not available.")
        raise
    except Exception as e:
        logger.error(f"Failed to adjust brightness: {e}")
        raise


async def _set_brightness_wmi(level: int) -> str:
    """Fallback: set brightness via WMI PowerShell command."""
    cmd = (
        f'(Get-WmiObject -Namespace root/WMI -Class '
        f'WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})'
    )
    result = subprocess.run(
        ["powershell", "-Command", cmd],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return f"Brightness set to {level}% (via WMI)."
    else:
        raise RuntimeError(f"WMI brightness control failed: {result.stderr}")


# ═══════════════════════════════════════════
# VOLUME CONTROL
# ═══════════════════════════════════════════


def _get_volume_interface():
    """Get the Windows audio endpoint volume interface."""
    from pycaw.pycaw import AudioUtilities

    devices = AudioUtilities.GetSpeakers()
    return devices.EndpointVolume


async def set_volume(level: float) -> str:
    """
    Set system volume to a specific level.

    Args:
        level: Volume from 0.0 (mute) to 1.0 (maximum).

    Returns:
        Confirmation message.
    """
    level = max(0.0, min(1.0, level))

    try:
        volume = _get_volume_interface()
        volume.SetMasterVolumeLevelScalar(level, None)
        percent = int(level * 100)
        logger.info(f"Volume set to {percent}%")
        return f"Volume set to {percent}%."
    except Exception as e:
        logger.error(f"Failed to set volume: {e}")
        raise


async def toggle_mute() -> str:
    """Toggle system mute on/off."""
    try:
        volume = _get_volume_interface()
        current_mute = volume.GetMute()
        volume.SetMute(not current_mute, None)
        state = "muted" if not current_mute else "unmuted"
        logger.info(f"System {state}")
        return f"System {state}."
    except Exception as e:
        logger.error(f"Failed to toggle mute: {e}")
        raise


# ═══════════════════════════════════════════
# POWER MANAGEMENT
# ═══════════════════════════════════════════


async def shutdown_pc(delay_seconds: int = 30) -> str:
    """
    Schedule a system shutdown.

    Args:
        delay_seconds: Seconds to wait before shutdown.

    Returns:
        Confirmation message.
    """
    try:
        subprocess.run(
            ["shutdown", "/s", "/t", str(delay_seconds)],
            check=True,
        )
        logger.info(f"Shutdown scheduled in {delay_seconds} seconds")
        return (
            f"Shutdown scheduled in {delay_seconds} seconds, sir. "
            f"Use 'cancel shutdown' to abort."
        )
    except Exception as e:
        logger.error(f"Failed to schedule shutdown: {e}")
        raise


async def restart_pc(delay_seconds: int = 10) -> str:
    """
    Schedule a system restart.

    Args:
        delay_seconds: Seconds to wait before restart.

    Returns:
        Confirmation message.
    """
    try:
        subprocess.run(
            ["shutdown", "/r", "/t", str(delay_seconds)],
            check=True,
        )
        logger.info(f"Restart scheduled in {delay_seconds} seconds")
        return f"Restart scheduled in {delay_seconds} seconds."
    except Exception as e:
        logger.error(f"Failed to schedule restart: {e}")
        raise


async def cancel_shutdown() -> str:
    """Cancel a scheduled shutdown or restart."""
    try:
        subprocess.run(["shutdown", "/a"], check=True)
        logger.info("Shutdown cancelled")
        return "Shutdown cancelled, sir."
    except Exception as e:
        logger.error(f"Failed to cancel shutdown: {e}")
        raise


async def lock_screen() -> str:
    """Lock the Windows workstation."""
    try:
        ctypes.windll.user32.LockWorkStation()
        logger.info("Workstation locked")
        return "Workstation locked."
    except Exception as e:
        logger.error(f"Failed to lock screen: {e}")
        raise


async def get_battery_level() -> str:
    """Get the current battery percentage and charging status."""
    try:
        import psutil
        battery = psutil.sensors_battery()
        if not battery:
            return "I cannot detect a battery. This device is likely running on AC power."
        
        percent = int(battery.percent)
        plugged = "plugged in and charging" if battery.power_plugged else "running on battery"
        
        logger.info(f"Battery checked: {percent}% ({plugged})")
        return f"Sir, your battery is at {percent}% and is currently {plugged}."
    except Exception as e:
        logger.error(f"Failed to get battery: {e}")
        return "I was unable to retrieve the battery status, sir."
