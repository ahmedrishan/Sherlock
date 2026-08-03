"""Wake word detection module using Picovoice Porcupine.

Monitors audio frames to trigger the voice assistant upon hearing the keyword 'Sherlock'.
"""

import config
from utils.logger import get_logger

logger = get_logger(__name__)

class WakeWordDetector:
    """Handles real-time keyword detection from microphonic inputs."""

    def __init__(self):
        """Initializes the wake word detector client."""
        logger.info("Initializing WakeWordDetector...")
        self.access_key = config.PICOVOICE_ACCESS_KEY
        self.porcupine = None
        
        if not self.access_key:
            logger.warning("Picovoice access key is missing. Wake word detection will not function.")

    def initialize(self):
        """Prepares the Picovoice Porcupine instance.

        Raises:
            ValueError: If access key is missing or invalid.
        """
        # TODO: Initialize pvporcupine.create(...)
        logger.info("WakeWordDetector initialized successfully.")

    def process_frame(self, pcm_frame: list[int]) -> bool:
        """Processes a single PCM frame of audio for wake word detection.

        Args:
            pcm_frame (list[int]): A list of 16-bit linear PCM audio samples.

        Returns:
            bool: True if the keyword was detected, False otherwise.
        """
        # TODO: Process frame with porcupine.process()
        return False

    def cleanup(self):
        """Releases the Picovoice Porcupine native library resources."""
        logger.info("Cleaning up WakeWordDetector...")
        # TODO: Call self.porcupine.delete()
