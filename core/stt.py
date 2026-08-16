"""Speech-to-Text (STT) module using faster-whisper.

Converts recorded audio payloads into transcribed text queries for brain processing.
Model loading is deferred until first use, so application startup stays fast.
"""

import tempfile

import scipy.io.wavfile as wav
import numpy as np

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class SpeechToText:
    """Handles speech transcription using a local faster-whisper model."""

    def __init__(self):
        """Initializes the SpeechToText settings without loading the model yet."""
        logger.info("Initializing SpeechToText...")
        self.model_size = getattr(config, "STT_MODEL_SIZE", "base")
        self.device = getattr(config, "STT_DEVICE", "cpu")
        self.compute_type = getattr(config, "STT_COMPUTE_TYPE", "int8")
        self.model = None

    def load_model(self):
        """Loads the Whisper model into memory, if not already loaded.

        Deferred loading is used so the app can start instantly and only pay
        the (multi-second) model load cost the first time transcription is
        actually needed.
        """
        if self.model is None:
            logger.info(
                f"Loading faster-whisper model '{self.model_size}' "
                f"on '{self.device}' ({self.compute_type})..."
            )
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                logger.error("faster-whisper is not installed. Please install 'faster-whisper'.")
                raise
            self.model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )

    def transcribe(self, audio_path: str) -> str:
        """Transcribes an audio file into text.

        Args:
            audio_path: Path to the recorded audio file (usually WAV).

        Returns:
            The transcribed text query, or an empty string if nothing was said.
        """
        self.load_model()
        logger.info(f"Transcribing audio file: {audio_path}")

        assert self.model is not None
        initial_prompt = "Sherlock voice assistant commands: play song on Spotify, open app, set timer, weather, Rishan, Trivandrum, Malappuram."
        segments, _ = self.model.transcribe(
            audio_path,
            beam_size=5,
            language="en",
            initial_prompt=initial_prompt,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()

        logger.info(f"Transcribed output: '{text}'")
        return text

    def transcribe_bytes(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribes raw PCM/WAV bytes directly, without a pre-saved file.

        This is the method to use with core.audio_recorder / session_manager,
        since captured utterances there come back as raw bytes rather than a
        file on disk.

        Args:
            audio_bytes: Raw int16 PCM audio data.
            sample_rate: Sample rate the audio was captured at.

        Returns:
            The transcribed text query, or an empty string if nothing was said.
        """
        if not audio_bytes:
            return ""

        samples = np.frombuffer(audio_bytes, dtype=np.int16)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            wav.write(temp_file.name, sample_rate, samples)
            return self.transcribe(temp_file.name)