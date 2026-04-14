"""
Stewie TTS Engine — Text-to-Speech with edge-tts and pyttsx3 fallback.

Provides natural-sounding speech synthesis using Microsoft Edge neural
voices, with an offline fallback via Windows SAPI5.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger


class TTSEngine:
    """
    Text-to-Speech engine with two backends:
    - Primary: edge-tts (Microsoft Edge neural voices — high quality)
    - Fallback: pyttsx3 (Windows SAPI5 — offline)
    """

    def __init__(self, voice: str = "en-US-GuyNeural"):
        self.voice = voice
        self._use_edge_tts = True

        # Verify edge-tts availability
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            logger.warning(
                "edge-tts not installed — using pyttsx3 fallback."
            )
            self._use_edge_tts = False

    async def speak(self, text: str) -> None:
        """
        Synthesize and play speech from text.

        Args:
            text: The text to speak aloud.
        """
        if not text:
            return

        logger.debug(f"Speaking: \"{text[:80]}...\"" if len(text) > 80 else f"Speaking: \"{text}\"")

        if self._use_edge_tts:
            await self._speak_edge(text)
        else:
            await self._speak_pyttsx3(text)

    async def _speak_edge(self, text: str) -> None:
        """Synthesize speech using edge-tts and play it."""
        try:
            import edge_tts

            # Generate audio to a temp file
            temp_file = tempfile.mktemp(suffix=".mp3", prefix="stewie_tts_")

            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(temp_file)

            # Play the audio
            await self._play_audio(temp_file)

            # Cleanup
            Path(temp_file).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"edge-tts failed: {e}. Falling back to pyttsx3.")
            await self._speak_pyttsx3(text)

    async def _speak_pyttsx3(self, text: str) -> None:
        """Synthesize speech using pyttsx3 (offline, SAPI5)."""
        loop = asyncio.get_event_loop()

        def _speak_sync():
            try:
                import pyttsx3

                engine = pyttsx3.init()

                # Configure voice
                voices = engine.getProperty("voices")
                # Try to find a male English voice
                for voice in voices:
                    if "male" in voice.name.lower() or "david" in voice.name.lower():
                        engine.setProperty("voice", voice.id)
                        break

                engine.setProperty("rate", 175)  # Words per minute
                engine.setProperty("volume", 0.9)

                engine.say(text)
                engine.runAndWait()
                engine.stop()

            except ImportError:
                logger.error("pyttsx3 not available — no TTS engine found.")
            except Exception as e:
                logger.error(f"pyttsx3 failed: {e}")

        await loop.run_in_executor(None, _speak_sync)

    async def _play_audio(self, file_path: str) -> None:
        """Play an audio file using sounddevice/soundfile or playsound."""
        loop = asyncio.get_event_loop()

        def _play_sync():
            try:
                # Try sounddevice + soundfile first
                import sounddevice as sd
                import soundfile as sf

                data, samplerate = sf.read(file_path)
                sd.play(data, samplerate)
                sd.wait()
            except ImportError:
                try:
                    # Fallback: use system default player
                    import os

                    os.startfile(file_path)
                    import time

                    time.sleep(3)  # Approximate playback time
                except Exception as e:
                    logger.error(f"Could not play audio: {e}")
            except Exception as e:
                logger.error(f"Audio playback error: {e}")

        await loop.run_in_executor(None, _play_sync)

    async def play_sound(self, file_path: str) -> None:
        """
        Play a sound effect (e.g., listening chime).

        Args:
            file_path: Path to the sound file.
        """
        if not Path(file_path).exists():
            logger.trace(f"Sound file not found: {file_path}")
            return

        await self._play_audio(file_path)

    def set_voice(self, voice_name: str) -> None:
        """Change the TTS voice."""
        self.voice = voice_name
        logger.info(f"TTS voice changed to: {voice_name}")
