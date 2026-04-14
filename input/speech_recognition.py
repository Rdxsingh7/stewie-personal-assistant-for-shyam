"""
Stewie Speech Recognition — Converts spoken audio to text.

Uses faster-whisper (CTranslate2 Whisper) for high-quality, local
speech-to-text. Falls back to Google Speech Recognition if needed.
"""

from __future__ import annotations

import asyncio
import io
import tempfile
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
from loguru import logger


class SpeechRecognizer:
    """
    Records audio after wake word detection and transcribes it.

    Listens until silence is detected (configurable threshold),
    then runs the audio through Whisper for transcription.
    """

    SAMPLE_RATE = 16000
    CHANNELS = 1
    DTYPE = "int16"
    MAX_RECORDING_SECONDS = 15
    SILENCE_THRESHOLD = 500  # RMS threshold for silence detection
    SILENCE_DURATION = 2.0  # Seconds of silence to stop recording

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _initialize_model(self):
        """Lazy-load the Whisper model."""
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info(
                f"Whisper model loaded (size={self.model_size}, device=cpu)"
            )
        except ImportError:
            logger.warning(
                "faster-whisper not available. "
                "Will use speech_recognition library as fallback."
            )
            self._model = None
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self._model = None

    async def listen_and_transcribe(self) -> Optional[str]:
        """
        Record audio from the microphone until silence, then transcribe.

        Returns:
            Transcribed text, or None if nothing was captured.
        """
        logger.info("Listening for speech...")

        # Record audio
        audio_data = await self._record_until_silence()
        if audio_data is None or len(audio_data) == 0:
            logger.warning("No audio captured.")
            return None

        # Transcribe
        transcript = await self._transcribe(audio_data)
        if transcript:
            logger.info(f"Transcription: \"{transcript}\"")
        return transcript

    async def _record_until_silence(self) -> Optional[np.ndarray]:
        """
        Record audio, stopping after SILENCE_DURATION seconds of silence
        or MAX_RECORDING_SECONDS.
        """
        loop = asyncio.get_event_loop()

        def _record():
            frames = []
            silence_frames = 0
            frames_per_second = self.SAMPLE_RATE // 1024
            max_silence_frames = int(
                self.SILENCE_DURATION * frames_per_second
            )
            max_total_frames = int(
                self.MAX_RECORDING_SECONDS * frames_per_second
            )

            try:
                with sd.InputStream(
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    dtype=self.DTYPE,
                    blocksize=1024,
                ) as stream:
                    for _ in range(max_total_frames):
                        chunk, _ = stream.read(1024)
                        frames.append(chunk.copy())

                        # Check for silence
                        rms = np.sqrt(np.mean(chunk.astype(float) ** 2))
                        if rms < self.SILENCE_THRESHOLD:
                            silence_frames += 1
                        else:
                            silence_frames = 0

                        if silence_frames >= max_silence_frames and len(frames) > frames_per_second:
                            logger.debug(
                                "Silence detected — stopping recording."
                            )
                            break

            except Exception as e:
                logger.error(f"Recording error: {e}")
                return None

            if frames:
                return np.concatenate(frames, axis=0)
            return None

        return await loop.run_in_executor(None, _record)

    async def _transcribe(self, audio_data: np.ndarray) -> Optional[str]:
        """Transcribe audio data to text."""
        if self._model is None:
            self._initialize_model()

        if self._model is not None:
            return await self._transcribe_whisper(audio_data)
        else:
            return await self._transcribe_fallback(audio_data)

    async def _transcribe_whisper(
        self, audio_data: np.ndarray
    ) -> Optional[str]:
        """Transcribe using faster-whisper."""
        loop = asyncio.get_event_loop()

        def _run_whisper():
            # Convert int16 to float32 for Whisper
            audio_float = audio_data.astype(np.float32) / 32768.0
            audio_flat = audio_float.flatten()

            segments, info = self._model.transcribe(
                audio_flat,
                language="en",
                beam_size=5,
                vad_filter=True,
            )

            text_parts = [segment.text.strip() for segment in segments]
            return " ".join(text_parts) if text_parts else None

        try:
            return await loop.run_in_executor(None, _run_whisper)
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return None

    async def _transcribe_fallback(
        self, audio_data: np.ndarray
    ) -> Optional[str]:
        """Fallback transcription using speech_recognition + Google API."""
        try:
            import speech_recognition as sr

            # Save audio to a temporary WAV file
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as f:
                temp_path = f.name
                with wave.open(f, "wb") as wav:
                    wav.setnchannels(self.CHANNELS)
                    wav.setsampwidth(2)  # 16-bit = 2 bytes
                    wav.setframerate(self.SAMPLE_RATE)
                    wav.writeframes(audio_data.tobytes())

            recognizer = sr.Recognizer()
            with sr.AudioFile(temp_path) as source:
                audio = recognizer.record(source)

            text = recognizer.recognize_google(audio)

            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

            return text if text else None

        except ImportError:
            logger.error(
                "Neither faster-whisper nor speech_recognition is available."
            )
            return None
        except Exception as e:
            logger.error(f"Fallback transcription failed: {e}")
            return None
