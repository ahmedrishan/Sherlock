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
        backup_word: str = "hey_jarvis",
        threshold: float = 0.5,
        sample_rate: int = 16000,
        model_path: str | None = None,
    ):
        """Initializes openWakeWord model for target word ('sherlock') and backup ('hey_jarvis')."""
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.target_word = target_word
        self.backup_word = backup_word
        self.is_listening = False
        self.active_keys: dict[str, str] = {}

        # Download/load openWakeWord default models if needed
        try:
            openwakeword.utils.download_models()
        except Exception as err:
            logger.warning(f"openWakeWord model download notice: {err}")

        # Resolve model path for custom 'sherlock' wake word
        resolved_path = self._resolve_model_path(model_path or getattr(config, "WAKE_WORD_MODEL_PATH", ""))

        models_to_load = []
        if resolved_path and os.path.exists(resolved_path):
            models_to_load.append(resolved_path)
            sherlock_key = Path(resolved_path).stem
            self.active_keys[sherlock_key] = self.target_word
            logger.info(f"Loading custom openWakeWord ONNX model for '{self.target_word}' from: {resolved_path}")
        else:
            models_to_load.append(self.target_word)
            self.active_keys[self.target_word] = self.target_word

        if self.backup_word and self.backup_word != self.target_word:
            models_to_load.append(self.backup_word)
            self.active_keys[self.backup_word] = f"{self.backup_word} (backup)"

        try:
            self.model = Model(
                wakeword_models=models_to_load,
                inference_framework="onnx",
            )
        except Exception as err:
            logger.warning(
                f"Could not load openWakeWord models {models_to_load}: {err}. "
                f"Falling back to built-in '{self.backup_word}' model."
            )
            self.model = Model(
                wakeword_models=[self.backup_word],
                inference_framework="onnx",
            )
            self.active_keys = {self.backup_word: f"{self.backup_word} (backup)"}

        logger.info(
            f"openWakeWord initialized for target: '{self.target_word}' "
            f"(Active models: {list(self.active_keys.keys())}, Threshold: {self.threshold})"
        )

    def _resolve_model_path(self, explicit_path: str) -> str | None:
        """Resolves path to custom ONNX wake word model file if present."""
        if explicit_path:
            candidate = Path(explicit_path)
            if not candidate.is_absolute():
                candidate = config.BASE_DIR / candidate
            if candidate.exists():
                return str(candidate)

        candidates = [
            config.BASE_DIR / "models" / f"{self.target_word}.onnx",
            config.BASE_DIR / "model" / f"{self.target_word}.onnx",
            config.BASE_DIR / f"{self.target_word}.onnx",
        ]
        for path in candidates:
            if path.exists():
                return str(path)
        return None

    def listen_for_wake_word(self) -> bool:
        """Listens continuously on a low-resource 16kHz stream until a wake word is detected."""
        chunk_size = 1280  # 80ms frame at 16kHz
        logger.info(f"👂 Listening for wake word ('{self.target_word}' / backup: '{self.backup_word}')...")
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
                    word_label, score = self._evaluate_predictions(prediction)

                    if score >= 0.10 and score < self.threshold:
                        logger.debug(
                            f"Wake word '{word_label}' partial activation: {score:.3f} (Threshold: {self.threshold})"
                        )

                    if score >= self.threshold:
                        logger.info(
                            f"⚡ Wake word '{word_label}' detected! (Score: {score:.2f})"
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
        word_label, score = self._evaluate_predictions(prediction)
        if score >= self.threshold:
            logger.info(f"⚡ Wake word '{word_label}' detected! (Score: {score:.2f})")
            self.model.reset()
            return True
        return False

    def _evaluate_predictions(self, prediction: dict | tuple | list) -> tuple[str, float]:
        """Extracts and evaluates scores for all active wake words, returning (best_label, best_score)."""
        pred_dict = {}
        if isinstance(prediction, dict):
            pred_dict = prediction
        elif isinstance(prediction, (tuple, list)) and len(prediction) > 0:
            if isinstance(prediction[0], dict):
                pred_dict = prediction[0]

        best_label = self.target_word
        max_score = 0.0

        for key, label in self.active_keys.items():
            val = pred_dict.get(key)
            if val is not None:
                try:
                    score = float(val)
                    if score > max_score:
                        max_score = score
                        best_label = label
                except (ValueError, TypeError):
                    pass

        return best_label, max_score

    def _extract_score(self, prediction: dict | tuple | list) -> float:
        """Extracts max score across active wake word models for backward compatibility."""
        _, score = self._evaluate_predictions(prediction)
        return score

    def cleanup(self):
        """Gracefully releases model state and resets detector resources."""
        logger.info("Cleaning up openWakeWord resources.")
        self.is_listening = False
        if hasattr(self, "model") and self.model is not None:
            self.model.reset()
