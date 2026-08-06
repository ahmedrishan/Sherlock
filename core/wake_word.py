"""On-device Wake Word Detection module using openWakeWord ('Sherlock').

Monitors 16kHz 16-bit mono microphone PCM audio stream in small chunks (1280 samples / 80ms)
and triggers when the target wake word prediction score exceeds threshold.
"""

import os
from pathlib import Path

import numpy as np
import openwakeword
import openwakeword.utils
from openwakeword.model import Model
import sounddevice as sd

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class WakeWordDetector:
    """Lightweight, resource-efficient wake-word detector using openWakeWord."""

    def __init__(
        self,
        target_word: str = "sherlock",
        threshold: float = 0.5,
        sample_rate: int = 16000,
        model_path: str | None = None,
    ):
        """Initializes openWakeWord model for the specified target word ('sherlock')."""
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.target_word = target_word
        self.is_listening = False

        # Download/load openWakeWord default models if needed
        try:
            openwakeword.utils.download_models()
        except Exception as err:
            logger.warning(f"openWakeWord model download notice: {err}")

        # Resolve model path for custom 'sherlock' wake word
        resolved_path = self._resolve_model_path(model_path or getattr(config, "WAKE_WORD_MODEL_PATH", ""))

        if resolved_path and os.path.exists(resolved_path):
            logger.info(f"Loading custom openWakeWord ONNX model for '{self.target_word}' from: {resolved_path}")
            self.model = Model(
                wakeword_models=[resolved_path],
                inference_framework="onnx",
            )
            self.target_word_key = Path(resolved_path).stem
        else:
            try:
                self.model = Model(
                    wakeword_models=[self.target_word],
                    inference_framework="onnx",
                )
                self.target_word_key = self.target_word
            except ValueError:
                fallback_word = "hey_jarvis"
                logger.info(
                    f"Custom wake word model '{self.target_word}.onnx' not found in ./models/. "
                    f"To use custom '{self.target_word}' wake word, place '{self.target_word}.onnx' into the ./models/ directory. "
                    f"Using built-in '{fallback_word}' as active hardware listener fallback."
                )
                self.target_word_key = fallback_word
                self.model = Model(
                    wakeword_models=[fallback_word],
                    inference_framework="onnx",
                )

        logger.info(
            f"openWakeWord initialized for target: '{self.target_word}' "
            f"(Active key: '{self.target_word_key}', Threshold: {self.threshold})"
        )

    def _resolve_model_path(self, explicit_path: str) -> str | None:
        """Resolves path to custom ONNX wake word model file if present."""
        if explicit_path and os.path.exists(explicit_path):
            return explicit_path

        candidates = [
            os.path.join(config.BASE_DIR, "models", f"{self.target_word}.onnx"),
            os.path.join(config.BASE_DIR, f"{self.target_word}.onnx"),
            os.path.join(config.BASE_DIR, "models", "sherlock.onnx"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def listen_for_wake_word(self) -> bool:
        """Listens continuously on a low-resource 16kHz stream until the wake word is detected."""
        chunk_size = 1280  # 80ms frame at 16kHz
        logger.info(f"👂 Listening for wake word ('{self.target_word}')...")
        self.is_listening = True

        try:
            with sd.InputStream(
                samplerate=self.sample_rate, channels=1, dtype="int16"
            ) as stream:
                while self.is_listening:
                    chunk, overflow = stream.read(chunk_size)
                    if overflow:
                        logger.debug("Audio stream overflow encountered during wake word listening.")

                    audio_frame = np.frombuffer(chunk, dtype=np.int16)

                    # Feed frame to openWakeWord
                    prediction = self.model.predict(audio_frame)
                    score = self._extract_score(prediction)

                    if score >= self.threshold:
                        logger.info(
                            f"⚡ Wake word '{self.target_word}' detected! (Score: {score:.2f})"
                        )
                        self.model.reset()
                        return True
        except Exception as e:
            logger.error(f"Error during wake word listening loop: {e}")
            raise
        finally:
            self.is_listening = False
        return False

    def process_frame(self, audio_frame: np.ndarray) -> bool:
        """Processes a single audio frame (numpy array of int16 PCM samples).

        Returns:
            bool: True if target wake word score exceeds threshold.
        """
        prediction = self.model.predict(audio_frame)
        score = self._extract_score(prediction)
        if score >= self.threshold:
            logger.info(f"⚡ Wake word '{self.target_word}' detected! (Score: {score:.2f})")
            self.model.reset()
            return True
        return False

    def _extract_score(self, prediction: dict | tuple | list) -> float:
        """Extracts target wake word score safely from dict/tuple/list predictions."""
        key = getattr(self, "target_word_key", self.target_word)
        if isinstance(prediction, dict):
            val = prediction.get(key)
            if val is None:
                val = prediction.get(self.target_word, 0.0)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0.0
        elif isinstance(prediction, (tuple, list)) and len(prediction) > 0:
            item = prediction[0]
            if isinstance(item, dict):
                val = item.get(key)
                if val is None:
                    val = item.get(self.target_word, 0.0)
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0
            elif isinstance(item, (int, float, np.number)):
                return float(item)
        return 0.0

    def cleanup(self):
        """Gracefully releases model state and resets detector resources."""
        logger.info("Cleaning up openWakeWord resources.")
        self.is_listening = False
        if hasattr(self, "model") and self.model is not None:
            self.model.reset()
