"""
Stewie Wake Word Detector — Listens for "Hey Stewie" to activate.

Uses openwakeword for offline, low-latency wake word detection.
Runs on a background thread and emits events when triggered.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Optional

import numpy as np
import sounddevice as sd
from loguru import logger

from core.event_bus import EventBus


class WakeWordDetector:
    """
    Continuously monitors the microphone for the wake phrase.

    On detection, emits a 'wake_detected' event via the EventBus, which
    triggers the Speech Recognizer to start recording.
    """

    SAMPLE_RATE = 16000
    CHUNK_SIZE = 1280  # ~80ms of audio at 16kHz

    def __init__(
        self,
        event_bus: EventBus,
        wake_phrase: str = "hey stewie",
        sensitivity: float = 0.6,
    ):
        self.event_bus = event_bus
        self.wake_phrase = wake_phrase
        self.sensitivity = sensitivity
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._model = None

    def _initialize_model(self):
        """Lazy-load the wake word model."""
        try:
            from openwakeword.model import Model

            self._model = Model(
                wakeword_models=[self.wake_phrase],
                inference_framework="onnx",
            )
            logger.info(
                f"Wake word model loaded for phrase: '{self.wake_phrase}'"
            )
        except ImportError:
            logger.warning(
                "openwakeword not installed. "
                "Using fallback keyword spotting."
            )
            self._model = None
        except Exception as e:
            logger.warning(
                f"Failed to load wake word model: {e}. "
                "Using fallback keyword spotting."
            )
            self._model = None

    async def start(self) -> None:
        """Start wake word detection in a background thread."""
        if self._running:
            logger.warning("Wake word detector already running.")
            return

        self._loop = asyncio.get_event_loop()
        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="WakeWordThread"
        )
        self._thread.start()
        logger.info("Wake word detector started — listening for activation.")

    def _listen_loop(self):
        """Background thread: continuously process audio chunks."""
        self._initialize_model()

        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=self.CHUNK_SIZE,
            ) as stream:
                while self._running:
                    audio_chunk, _ = stream.read(self.CHUNK_SIZE)
                    audio_data = np.squeeze(audio_chunk)

                    if self._model is not None:
                        self._process_with_model(audio_data)
                    # Fallback: wait for explicit trigger via event
        except Exception as e:
            logger.error(f"Wake word detector error: {e}")
            self._running = False

    def _process_with_model(self, audio_data: np.ndarray):
        """Process an audio chunk through the wake word model."""
        if self._paused:
            return

        prediction = self._model.predict(audio_data)

        # Check all wake word scores
        for model_name, score in prediction.items():
            if score >= self.sensitivity:
                logger.info(
                    f"Wake word detected! "
                    f"(model={model_name}, score={score:.3f})"
                )
                # Schedule the event emission on the main event loop
                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.event_bus.emit("wake_detected"),
                        self._loop,
                    )
                # Brief cooldown to prevent double triggers
                import time

                time.sleep(1.5)

    async def wait_for_wake_word(self) -> None:
        """
        Block until the wake word is detected.

        This is a convenience method for the main loop that uses
        an asyncio Event for clean async waiting.
        """
        wake_event = asyncio.Event()

        async def _on_wake(**kwargs):
            wake_event.set()

        self.event_bus.subscribe("wake_detected", _on_wake)

        try:
            if not self._running:
                await self.start()
            await wake_event.wait()
        finally:
            self.event_bus.unsubscribe("wake_detected", _on_wake)

    async def stop(self) -> None:
        """Stop the wake word detector."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Wake word detector stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    def pause(self) -> None:
        """Pause detection (e.g., when STT is listening or TTS is speaking)."""
        self._paused = True

    def resume(self) -> None:
        """Resume detection."""
        self._paused = False
