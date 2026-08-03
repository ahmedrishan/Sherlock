"""Sherlock — conversational session manager.

State machine:

    SLEEPING --(wake word heard)--> ACTIVE
    ACTIVE   --(shutdown phrase heard)--> SLEEPING
    ACTIVE   --(60s with no speech)--> SLEEPING   [auto-sleep]

While ACTIVE, every recognized utterance is sent straight to the brain and
answered out loud — no need to repeat the wake word between questions.
The auto-sleep timer resets every time you say something.

This module orchestrates other pieces that must exist for it to fully run:
    core.wakeword.WakeWordDetector.process(pcm_chunk: bytes) -> bool
    core.stt.transcribe(wav_bytes_or_path) -> str
    core.tts.speak(text: str) -> None
    brain.llm_client.ask(text: str) -> str
Stub versions are provided at the bottom of this file so it runs standalone
for testing before those pieces are wired in for real.
"""

import tempfile
import time
from enum import Enum, auto

import numpy as np
import scipy.io.wavfile as wav

from utils.logger import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    """Captures 16kHz, 16-bit mono microphone audio streams and WAV files."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """Initializes the AudioRecorder configuration."""
        logger.info("Initializing AudioRecorder...")
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording: list[np.ndarray] = []
        self.is_recording = False

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
        """Starts continuous audio stream capture."""
        logger.info("AudioRecorder: Recording started.")
        self.is_recording = True

    def stop_recording(self) -> None:
        """Stops continuous audio stream capture."""
        logger.info("AudioRecorder: Recording stopped.")
        self.is_recording = False

    def read_chunk(self, timeout: float = 0.5) -> bytes:
        """Reads a chunk of raw PCM audio bytes."""
        if not self.is_recording:
            return b""
        time.sleep(min(timeout, 0.05))
        return b""


# ---- Tunables ----
SHUTDOWN_PHRASES = {
    "shutdown", "shut down", "go to sleep", "goodbye sherlock",
    "stop listening", "that will be all", "sleep now",
}
AUTO_SLEEP_SECONDS = 60        # inactivity limit before auto-sleep
SILENCE_TAIL_SECONDS = 1.0     # trailing silence that ends one utterance
MAX_UTTERANCE_SECONDS = 15     # hard cap so it never records forever
VOICE_RMS_THRESHOLD = 500      # int16 RMS energy — tune to your mic/room
POLL_TIMEOUT = 0.5             # how long read_chunk waits before giving up


class State(Enum):
    SLEEPING = auto()
    ACTIVE = auto()


class SherlockSession:
    def __init__(self, wake_detector, transcribe_fn, speak_fn, ask_fn):
        self.recorder = AudioRecorder()
        self.wake_detector = wake_detector
        self.transcribe = transcribe_fn
        self.speak = speak_fn
        self.ask = ask_fn
        self.state = State.SLEEPING

    # ---------- Main loop ----------

    def run_forever(self):
        logger.info("Sherlock is asleep. Say the wake word to begin.")
        while True:
            if self.state == State.SLEEPING:
                self._wait_for_wake_word()
                self.state = State.ACTIVE
                self.speak("Yes? I'm listening.")
            else:
                self._conversation_loop()
                self.state = State.SLEEPING
                logger.info("Sherlock is asleep. Say the wake word to begin.")

    # ---------- Sleeping: wake word only ----------

    def _wait_for_wake_word(self):
        self.recorder.start_recording()
        try:
            while True:
                chunk = self.recorder.read_chunk(timeout=POLL_TIMEOUT)
                if not chunk:
                    continue
                if self.wake_detector.process(chunk):
                    logger.info("Wake word detected.")
                    return
        finally:
            self.recorder.stop_recording()

    # ---------- Active: ongoing conversation ----------

    def _conversation_loop(self):
        self.recorder.start_recording()
        last_interaction = time.time()
        try:
            while True:
                audio = self._capture_one_utterance()

                if audio is None:
                    if time.time() - last_interaction >= AUTO_SLEEP_SECONDS:
                        logger.info("No input for a minute — auto-sleeping.")
                        return
                    continue

                last_interaction = time.time()
                text = self.transcribe(audio).strip()
                if not text:
                    continue

                logger.info(f"Heard: {text}")

                if self._is_shutdown_phrase(text):
                    self.speak("Goodbye. Call me whenever you need me.")
                    return

                response = self.ask(text)
                self.speak(response)
        finally:
            self.recorder.stop_recording()

    # ---------- Utterance capture with simple voice-activity detection ----------

    def _capture_one_utterance(self):
        """Waits for speech to start, records until trailing silence or the
        max duration, and returns the raw audio bytes. Returns None if no
        speech was detected at all within one polling window (caller decides
        whether that means 'keep waiting' or 'time to auto-sleep')."""
        buffer = bytearray()
        speaking = False
        silence_start = None
        utterance_start = None

        while True:
            chunk = self.recorder.read_chunk(timeout=POLL_TIMEOUT)
            if not chunk:
                return None if not speaking else self._finalize(buffer)

            is_voice = self._is_voice(chunk)
            now = time.time()

            if is_voice:
                if not speaking:
                    speaking = True
                    utterance_start = now
                    logger.info("🎤 Speech detected...")
                buffer.extend(chunk)
                silence_start = None
            elif speaking:
                buffer.extend(chunk)  # keep the trailing silence, sounds natural
                silence_start = silence_start or now
                if now - silence_start >= SILENCE_TAIL_SECONDS:
                    return self._finalize(buffer)

            if utterance_start is not None and now - utterance_start >= MAX_UTTERANCE_SECONDS:
                logger.info("Max utterance length reached, cutting off.")
                return self._finalize(buffer)

    @staticmethod
    def _is_voice(chunk: bytes) -> bool:
        samples = np.frombuffer(chunk, dtype=np.int16)
        if samples.size == 0:
            return False
        rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
        return rms >= VOICE_RMS_THRESHOLD

    @staticmethod
    def _finalize(buffer: bytearray) -> bytes:
        return bytes(buffer)

    @staticmethod
    def _is_shutdown_phrase(text: str) -> bool:
        lowered = text.lower()
        return any(phrase in lowered for phrase in SHUTDOWN_PHRASES)


# ---------------------------------------------------------------------------
# Stub implementations — replace these with the real modules as you build
# Phases 1-4. Lets you run this file standalone to test the state machine
# and VAD logic before STT/TTS/wake-word/brain are wired in.
# ---------------------------------------------------------------------------

class _StubWakeDetector:
    """Replace with core.wakeword.WakeWordDetector (Porcupine)."""
    def process(self, pcm_chunk: bytes) -> bool:
        return input("[stub] Press Enter to simulate wake word...") == ""


def _stub_transcribe(audio_bytes: bytes) -> str:
    """Replace with core.stt.transcribe (faster-whisper)."""
    return input("[stub] Type what you 'said': ")


def _stub_speak(text: str) -> None:
    """Replace with core.tts.speak (Piper/ElevenLabs)."""
    print(f"Sherlock: {text}")


def _stub_ask(text: str) -> str:
    """Replace with brain.llm_client.ask (Gemini function-calling call)."""
    return f"You said: '{text}'. (Gemini brain not wired in yet.)"


if __name__ == "__main__":
    session = SherlockSession(
        wake_detector=_StubWakeDetector(),
        transcribe_fn=_stub_transcribe,
        speak_fn=_stub_speak,
        ask_fn=_stub_ask,
    )
    session.run_forever()