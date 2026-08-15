"""Sherlock — low-latency audio recorder and conversational session manager.

Provides:
  - AudioRecorder: continuous streaming, low-latency VAD (Voice Activity Detection),
    and Push-to-Talk audio input.
  - SherlockSession: state-machine orchestrator (SLEEPING <-> ACTIVE).

State machine:
    SLEEPING --(wake word heard)--> ACTIVE
    ACTIVE   --(shutdown phrase heard)--> SLEEPING
    ACTIVE   --(60s with no speech)--> SLEEPING   [auto-sleep]
"""

import queue
import tempfile
import time
from enum import Enum, auto

import numpy as np
import scipy.io.wavfile as wav

from utils.logger import get_logger

logger = get_logger(__name__)

# ---- Tunables ----
SHUTDOWN_PHRASES = {
    "shutdown", "shut down", "go to sleep", "goodbye sherlock",
    "stop listening", "that will be all", "sleep now",
}
AUTO_SLEEP_SECONDS = 60        # inactivity limit before auto-sleep
SILENCE_TAIL_SECONDS = 1.0     # trailing silence that ends one utterance
MAX_UTTERANCE_SECONDS = 15     # hard cap so it never records forever
VOICE_RMS_THRESHOLD = 500      # int16 RMS energy threshold for voice detection
POLL_TIMEOUT = 0.1             # polling interval in seconds for queue reads


class AudioRecorder:
    """Captures 16kHz, 16-bit mono microphone audio streams, low-latency VAD chunks, and WAV files."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """Initializes the AudioRecorder configuration."""
        logger.info("Initializing AudioRecorder...")
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording: list[np.ndarray] = []
        self.is_recording = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._stream = None

    def record_until_keypress(self) -> str:
        """Records microphone audio until the user presses [ENTER], then saves as a WAV file.

        Returns:
            str: Path to the temporary .wav file containing recorded audio.
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice package is not installed. Install via: pip install sounddevice")
            raise ModuleNotFoundError("The 'sounddevice' package is required for recording audio.")

        self.recording = []
        self.is_recording = True
        logger.info("🎤 Listening... Speak now.")

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio stream status: {status}")
            if self.is_recording:
                self.recording.append(indata.copy())

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=callback,
        ):
            input("\nPress [ENTER] to stop recording...\n")
            self.is_recording = False

        if self.recording:
            audio_data = np.concatenate(self.recording, axis=0)
        else:
            audio_data = np.array([], dtype=np.int16)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        wav.write(temp_file.name, self.sample_rate, audio_data)
        logger.info(f"Audio buffer saved to {temp_file.name}")
        return temp_file.name

    def start_recording(self) -> None:
        """Starts continuous non-blocking audio stream capture into a thread-safe queue."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice package is not installed.")
            raise ModuleNotFoundError("The 'sounddevice' package is required for streaming audio.")

        if self.is_recording:
            return

        self._audio_queue = queue.Queue()
        self.is_recording = True

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio stream status: {status}")
            if self.is_recording:
                self._audio_queue.put(indata.copy().tobytes())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=callback,
            blocksize=1280,  # 80ms chunks
        )
        self._stream.start()
        logger.info("AudioRecorder: Continuous audio streaming started.")

    def stop_recording(self) -> None:
        """Stops continuous audio stream capture."""
        self.is_recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug(f"Stream cleanup notice: {e}")
            self._stream = None
        logger.info("AudioRecorder: Continuous audio streaming stopped.")

    def read_chunk(self, timeout: float = POLL_TIMEOUT) -> bytes:
        """Reads a chunk of raw PCM audio bytes from the queue with specified timeout."""
        if not self.is_recording:
            return b""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return b""

    def record_vad_utterance(
        self,
        silence_tail: float = SILENCE_TAIL_SECONDS,
        max_duration: float = MAX_UTTERANCE_SECONDS,
        rms_threshold: int = VOICE_RMS_THRESHOLD,
        inactivity_timeout: float | None = None,
    ) -> str | None:
        """Records an utterance dynamically using Voice Activity Detection (VAD).

        Waits for voice activity, captures audio until trailing silence, max duration, or inactivity timeout,
        and saves to a temporary WAV file.

        Returns:
            str | None: Path to WAV file, or None if no speech was detected.
        """
        self.start_recording()
        buffer = bytearray()
        speaking = False
        silence_start = None
        utterance_start = None
        listen_start = time.time()

        try:
            while True:
                now = time.time()
                if not speaking and inactivity_timeout is not None and (now - listen_start) >= inactivity_timeout:
                    logger.info(f"VAD: Inactivity timeout ({inactivity_timeout}s) reached with no speech.")
                    break

                chunk = self.read_chunk(timeout=POLL_TIMEOUT)
                if not chunk:
                    if speaking:
                        break
                    continue

                samples = np.frombuffer(chunk, dtype=np.int16)
                rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2)) if samples.size > 0 else 0.0
                is_voice = rms >= rms_threshold

                if is_voice:
                    if not speaking:
                        speaking = True
                        utterance_start = now
                        logger.info("🎤 Speech detected (VAD active)...")
                    buffer.extend(chunk)
                    silence_start = None
                elif speaking:
                    buffer.extend(chunk)  # keep trailing silence for natural transition
                    if silence_start is None:
                        silence_start = now
                    if now - silence_start >= silence_tail:
                        logger.info("VAD: Trailing silence detected, ending utterance.")
                        break

                if utterance_start is not None and (now - utterance_start) >= max_duration:
                    logger.info("VAD: Max utterance duration reached, cutting off.")
                    break
        finally:
            self.stop_recording()

        if not buffer or not speaking:
            return None

        audio_data = np.frombuffer(buffer, dtype=np.int16)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        wav.write(temp_file.name, self.sample_rate, audio_data)
        logger.info(f"VAD utterance captured ({len(audio_data) / self.sample_rate:.2f}s) -> {temp_file.name}")
        return temp_file.name

    def record_command_with_vad(
        self,
        silence_duration: float = 0.9,
        speech_threshold: float = 500.0,
        max_duration: float = MAX_UTTERANCE_SECONDS,
        inactivity_timeout: float | None = None,
    ) -> str | None:
        """Records a user voice command using Voice Activity Detection (VAD).

        Args:
            silence_duration (float): Trailing silence duration in seconds to stop recording.
            speech_threshold (float): RMS energy threshold to detect voice activity.
            max_duration (float): Maximum recording duration cap.
            inactivity_timeout (float | None): Optional timeout in seconds to wait for initial speech.

        Returns:
            str | None: Path to WAV file, or None if no speech was captured.
        """
        return self.record_vad_utterance(
            silence_tail=silence_duration,
            max_duration=max_duration,
            rms_threshold=int(speech_threshold),
            inactivity_timeout=inactivity_timeout,
        )


class State(Enum):
    SLEEPING = auto()
    ACTIVE = auto()


class SherlockSession:
    """Orchestrates continuous voice assistant state machine."""

    def __init__(self, wake_detector, transcribe_fn, speak_fn, ask_fn):
        self.recorder = AudioRecorder()
        self.wake_detector = wake_detector
        self.transcribe = transcribe_fn
        self.speak = speak_fn
        self.ask = ask_fn
        self.state = State.SLEEPING

    def run_forever(self):
        """Runs the main hands-free wake word -> active conversation loop indefinitely."""
        logger.info("Sherlock session active. Say the wake word to begin.")
        while True:
            if self.state == State.SLEEPING:
                self._wait_for_wake_word()
                self.state = State.ACTIVE
                self.speak("Yes? I'm listening.")
            else:
                self._conversation_loop()
                self.state = State.SLEEPING
                logger.info("Sherlock is asleep. Say the wake word to begin.")

    def _wait_for_wake_word(self):
        if hasattr(self.wake_detector, "listen_for_wake_word"):
            self.wake_detector.listen_for_wake_word()
        else:
            self.recorder.start_recording()
            try:
                while True:
                    chunk = self.recorder.read_chunk(timeout=POLL_TIMEOUT)
                    if not chunk:
                        continue
                    audio_frame = np.frombuffer(chunk, dtype=np.int16)
                    if self.wake_detector.process_frame(audio_frame):
                        logger.info("Wake word detected.")
                        return
            finally:
                self.recorder.stop_recording()

    def _conversation_loop(self):
        last_interaction = time.time()
        while True:
            wav_path = self.recorder.record_vad_utterance()

            if wav_path is None:
                if time.time() - last_interaction >= AUTO_SLEEP_SECONDS:
                    logger.info("No speech detected for 60 seconds — auto-sleeping.")
                    return
                continue

            last_interaction = time.time()
            text = self.transcribe(wav_path).strip()
            if not text:
                continue

            logger.info(f"Heard: {text}")

            if self._is_shutdown_phrase(text):
                self.speak("Goodbye. Call me whenever you need me.")
                return

            response = self.ask(text)
            self.speak(response)

    @staticmethod
    def _is_shutdown_phrase(text: str) -> bool:
        lowered = text.lower()
        return any(phrase in lowered for phrase in SHUTDOWN_PHRASES)