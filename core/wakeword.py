"""Wake word detection module compatibility wrapper.

Re-exports WakeWordDetector from core.wake_word for openWakeWord ('sherlock').
"""

from core.wake_word import WakeWordDetector

__all__ = ["WakeWordDetector"]
