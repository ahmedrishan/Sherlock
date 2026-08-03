"""Speech-to-Text (STT) module using faster-whisper.

Converts recorded audio payloads into transcribed text queries for brain processing.
"""

import config
from utils.logger import get_logger

logger = get_logger(__name__)

class SpeechToText:
    """Handles speech transcription using localized faster-whisper models."""

    def __init__(self):
        """Initializes the SpeechToText model settings."""
        logger.info("Initializing SpeechToText...")
        self.model_size = config.STT_MODEL_SIZE
        self.device = config.STT_DEVICE
        self.model = None

    def load_model(self):
        """Loads the Whisper model into memory.

        Deferred loading is used to speed up initial application startup.
        """
        logger.info(f"Loading faster-whisper model '{self.model_size}' on '{self.device}'...")
        # TODO: Initialize WhisperModel(self.model_size, device=self.device)

    def transcribe(self, audio_path: str) -> str:
        """Transcribes an audio file into text.

        Args:
            audio_path (str): Path to the recorded audio file (usually WAV).

        Returns:
            str: The transcribed text query.
        """
        logger.info(f"Transcribing audio file: {audio_path}")
        if self.model is None:
            self.load_model()

        # TODO: Run transcription on model
        # segments, info = self.model.transcribe(audio_path, beam_size=5)
        # text = "".join([segment.text for segment in segments])
        
        return "This is a placeholder transcription from Sherlock."
