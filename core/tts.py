"""Text-to-Speech (TTS) module.

Converts textual brain responses into audible speech outputs using ElevenLabs or local TTS engines.
"""

import io
import os
import re
import pygame

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class TextToSpeech:
    """Handles text-to-speech synthesis and non-blocking in-memory voice playback."""

    def __init__(self):
        """Initializes Pygame mixer and TTS client provider."""
        logger.info("Initializing TextToSpeech engine...")
        self.provider = getattr(config, "TTS_PROVIDER", "elevenlabs").lower()
        self.api_key = os.getenv("ELEVENLABS_API_KEY") or getattr(config, "ELEVENLABS_API_KEY", "")
        self.voice_id = getattr(config, "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel voice ID
        self.model_id = getattr(config, "ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")

        self.mixer_active = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.mixer_active = True
            logger.info("Pygame audio mixer initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize Pygame mixer: {e}. Audio playback will be bypassed.")

        self.eleven_client = None
        if self.provider == "elevenlabs":
            if self.api_key:
                try:
                    from elevenlabs.client import ElevenLabs
                    self.eleven_client = ElevenLabs(api_key=self.api_key)
                    logger.info("ElevenLabs client initialized successfully.")
                except Exception as e:
                    logger.error(f"Failed to initialize ElevenLabs client: {e}")
            else:
                logger.warning("ELEVENLABS_API_KEY is not configured. TTS will run in bypass mode.")

    def speak(self, text: str) -> None:
        """Synthesizes text into speech and plays it back asynchronously via memory buffer.

        Args:
            text (str): The text response to speak.
        """
        if not text or not text.strip():
            return

        # Strip markdown syntax for clean spoken delivery
        clean_text = re.sub(r"[*_`#\-\[\]]", "", text).strip()
        if not clean_text:
            return

        logger.info(f"Synthesizing speech for: '{clean_text}' via provider '{self.provider}'")

        if self.provider == "elevenlabs":
            self._speak_elevenlabs(clean_text)
        elif self.provider == "piper":
            self._speak_piper(clean_text)
        else:
            self._speak_local(clean_text)

    def _speak_elevenlabs(self, text: str) -> None:
        """Generates speech via ElevenLabs low-latency API and plays via BytesIO memory buffer."""
        if not self.eleven_client or not self.api_key:
            logger.warning(f"[TTS Bypass] (No ELEVENLABS_API_KEY configured) Sherlock would say: '{text}'")
            return

        if not self.mixer_active:
            logger.warning(f"[TTS Bypass] (Audio mixer disabled) Sherlock would say: '{text}'")
            return

        try:
            logger.info(f"ElevenLabs TTS synthesis started (model: {self.model_id})...")
            audio_stream = self.eleven_client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model_id
            )
            audio_bytes = b"".join(audio_stream)
            sound_buffer = io.BytesIO(audio_bytes)

            pygame.mixer.music.load(sound_buffer)
            pygame.mixer.music.play()

            # Tick wait until audio completes before proceeding
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            logger.info("ElevenLabs speech playback completed.")
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}", exc_info=True)
            logger.warning(f"[TTS Bypass] Sherlock would say: '{text}'")

    def _speak_piper(self, text: str) -> None:
        """Local offline TTS placeholder for Piper / VITS engine."""
        logger.info(f"[Piper TTS Stub] Sherlock: '{text}'")

    def _speak_local(self, text: str) -> None:
        """Fallback local logger TTS output."""
        logger.info(f"[Local TTS] Sherlock: '{text}'")

