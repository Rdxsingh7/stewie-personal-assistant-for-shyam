"""
Stewie Audio Utilities — Helper functions for audio stream management.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from loguru import logger


def get_audio_devices() -> list[dict]:
    """List available audio input devices."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                input_devices.append(
                    {
                        "id": i,
                        "name": device["name"],
                        "channels": device["max_input_channels"],
                        "sample_rate": device["default_samplerate"],
                    }
                )
        return input_devices
    except Exception as e:
        logger.error(f"Failed to query audio devices: {e}")
        return []


def get_default_input_device() -> Optional[dict]:
    """Get the default audio input device."""
    try:
        import sounddevice as sd

        device_info = sd.query_devices(kind="input")
        return {
            "name": device_info["name"],
            "channels": device_info["max_input_channels"],
            "sample_rate": device_info["default_samplerate"],
        }
    except Exception as e:
        logger.error(f"Failed to get default input device: {e}")
        return None


def compute_rms(audio_data: np.ndarray) -> float:
    """Compute the RMS (root mean square) of audio data."""
    return float(np.sqrt(np.mean(audio_data.astype(float) ** 2)))


def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
    """Normalize audio to float32 range [-1.0, 1.0]."""
    if audio_data.dtype == np.int16:
        return audio_data.astype(np.float32) / 32768.0
    elif audio_data.dtype == np.float32:
        return audio_data
    else:
        return audio_data.astype(np.float32) / np.max(np.abs(audio_data))
