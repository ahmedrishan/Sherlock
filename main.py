"""Application entry point and continuous hands-free execution loop for Sherlock (Mini Jarvis).

Pipeline Architecture:
  WakeWordDetector (openWakeWord "sherlock")
  -> AudioRecorder (Low-Latency VAD 0.9s timeout)
  -> SpeechToText (faster-whisper)
  -> Gemini GenAI ReAct Brain (2.5-Flash + Function Calling)
  -> TextToSpeech Engine (ElevenLabs / Pygame)
"""

import os
import sys
from typing import Dict, Callable

from google import genai
from google.genai import types

import config
from utils.logger import get_logger

# Import core hardware & voice modules
from core.wake_word import WakeWordDetector
from core.audio_recorder import AudioRecorder
from core.stt import SpeechToText
from core.tts import TextToSpeech

# Import brain prompt template
from brain.prompt_template import SHERLOCK_SYSTEM_PROMPT

# Import baseline system tools
from tools.weather import get_weather
from tools.timer import set_timer
from tools.app_opener import open_app

logger = get_logger(__name__)

# Register baseline tool mapping
TOOLS_LIST = [get_weather, set_timer, open_app]
TOOL_MAP: Dict[str, Callable] = {
    "get_weather": get_weather,
    "set_timer": set_timer,
    "open_app": open_app,
}

# Global TTS helper delegate
_tts_engine = None


def get_tts_engine() -> TextToSpeech:
    """Returns the singleton TextToSpeech instance."""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TextToSpeech()
    return _tts_engine


def speak_text(text: str):
    """Converts response text to speech and plays audio using modular TTS engine."""
    get_tts_engine().speak(text)


def create_chat_session(client: genai.Client, model_name: str):
    """Creates a Gemini chat session with native function calling and low temperature.

    Args:
        client (genai.Client): Initialized GenAI client instance.
        model_name (str): Gemini model identifier (e.g. 'gemini-2.5-flash').

    Returns:
        Chat: GenAI chat session object.
    """
    return client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=SHERLOCK_SYSTEM_PROMPT,
            temperature=0.2,  # Low variance for deterministic tool routing
            tools=TOOLS_LIST,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )
    )


def run_react_loop(chat, user_query: str) -> str:
    """Executes the ReAct (Reasoning + Acting) decision engine loop for a user query.

    Evaluates user input, intercepts function calls, logs arguments and observations,
    and feeds function responses back to Gemini until a final text response is synthesized.

    Args:
        chat: Active GenAI chat session.
        user_query (str): Input text from user or STT transcription.

    Returns:
        str: Final natural language response text.
    """
    logger.info(f"Processing user query: '{user_query}'")
    response = chat.send_message(user_query)

    step = 0
    max_steps = 5

    # ReAct Loop: Intercept function calls and send observations back
    while response.function_calls and step < max_steps:
        step += 1
        for call in response.function_calls:
            func_name = call.name
            func_args = call.args or {}

            # Log ReAct Step: Tool requested & parameters passed
            logger.info(f"🤖 [ReAct Step {step}] Tool requested: '{func_name}' with args: {func_args}")
            print(f"🤖 [ReAct Step {step}] Tool: '{func_name}' | Args: {func_args}")

            # Execute tool locally
            tool_fn = TOOL_MAP.get(func_name)
            if tool_fn:
                try:
                    observation = tool_fn(**func_args)
                except Exception as e:
                    logger.error(f"Error executing {func_name}: {e}")
                    observation = f"Error executing tool {func_name}: {e}"
            else:
                logger.error(f"Tool '{func_name}' requested but not registered in TOOL_MAP.")
                observation = f"Error: Tool '{func_name}' is not registered."

            # Log ReAct Step: Observation returned
            logger.info(f"🔍 [ReAct Step {step}] Observation returned: {observation}")
            print(f"🔍 [ReAct Step {step}] Observation: {observation}")

            # Feed observation back to Gemini chat session
            response_part = types.Part.from_function_response(
                name=func_name,
                response={"result": observation}
            )
            response = chat.send_message(response_part)

    final_text = response.text or "Request completed."
    logger.info(f"Synthesized Response: '{final_text}'")
    return final_text


def main():
    """Initializes Sherlock hands-free Voice Assistant and runs continuous execution loop."""
    logger.info("Initializing Sherlock Voice Assistant (Mini Jarvis) Phase 4 Pipeline...")

    gemini_key = os.getenv("GEMINI_API_KEY", config.GEMINI_API_KEY)
    if not gemini_key:
        logger.critical("GEMINI_API_KEY is not configured in environment or config.py.")
        print("❌ Error: GEMINI_API_KEY is missing. Please add it to your .env file.")
        sys.exit(1)

    model_name = getattr(config, "GEMINI_MODEL", "gemini-2.5-flash")
    if not model_name or "1.5" in model_name:
        model_name = "gemini-2.5-flash"

    try:
        client = genai.Client(api_key=gemini_key)
        chat_session = create_chat_session(client, model_name=model_name)
        logger.info(f"Gemini GenAI client initialized with model '{model_name}'.")
    except Exception as e:
        logger.critical(f"Failed to initialize Gemini GenAI client: {e}", exc_info=True)
        sys.exit(1)

    # 1. Instantiate Pipeline Modules
    logger.info("Instantiating pipeline hardware & speech modules...")
    wake_word_detector = WakeWordDetector(target_word="sherlock", threshold=0.5)
    recorder = AudioRecorder(sample_rate=16000)
    stt_engine = SpeechToText()
    tts_engine = get_tts_engine()

    print("\n==================================================")
    print("         Sherlock Voice Assistant (Mini Jarvis)")
    print("           Hands-Free Always-Listening Mode")
    print("==================================================")
    print(f"Wake Word:    openWakeWord ('sherlock')")
    print(f"VAD Timeout:  0.9s trailing silence cutoff")
    print(f"STT Engine:   faster-whisper ({config.STT_MODEL_SIZE})")
    print(f"Brain LLM:    Gemini GenAI ({model_name})")
    print(f"TTS Provider: {config.TTS_PROVIDER} (ElevenLabs / Pygame)")
    print("==================================================")
    print("Sherlock is ready and listening for 'Sherlock' (Press Ctrl+C to stop)...")
    print("==================================================\n")

    # 2. Hands-Free Execution Loop
    try:
        while True:
            # a. Block silently on wake_word_detector.listen_for_wake_word()
            triggered = wake_word_detector.listen_for_wake_word()
            if not triggered:
                continue

            # b. Print wake word detection trigger
            print("\n⚡ Wake word 'Sherlock' detected! Listening for command...")

            # c. Execute recorder.record_command_with_vad(silence_duration=0.9, speech_threshold=500.0)
            wav_path = recorder.record_command_with_vad(silence_duration=0.9, speech_threshold=500.0)

            # d. If wav_path is empty or invalid, reset back to listening
            if not wav_path or not os.path.exists(wav_path):
                print("Sherlock: No speech detected. Returning to sleep.")
                print("sleeping... Listening for 'Sherlock'...\n")
                continue

            # e. Execute STT transcription
            try:
                user_text = stt_engine.transcribe(wav_path).strip()
            except Exception as stt_err:
                logger.error(f"STT transcription error: {stt_err}")
                print(f"⚠️ [STT Error]: {stt_err}")
                print("sleeping... Listening for 'Sherlock'...\n")
                continue

            # f. Print transcribed text
            if not user_text:
                print("Sherlock: I didn't catch any words. Returning to sleep.")
                print("sleeping... Listening for 'Sherlock'...\n")
                continue

            print(f"You (Voice): {user_text}")

            # g. Pass user_text into Gemini 2.5 ReAct tool loop
            try:
                final_response = run_react_loop(chat_session, user_text)
            except Exception as brain_err:
                logger.error(f"ReAct decision engine error: {brain_err}")
                final_response = "I encountered an issue processing your request."

            # h. Pass Gemini's final text response to TTS engine
            print(f"Sherlock: {final_response}")
            speak_text(final_response)

            # i. Print sleeping notification and reset loop
            print("sleeping... Listening for 'Sherlock'...\n")

    except KeyboardInterrupt:
        print("\n\nSherlock: Goodbye. Shutting down hands-free listener...")
        logger.info("KeyboardInterrupt received. Initiating graceful shutdown...")
    except Exception as e:
        logger.critical(f"Unhandled exception in hands-free loop: {e}", exc_info=True)
        print(f"\n⚠️ [System Crash]: {e}")
    finally:
        # 3. Clean Exit & Graceful Cleanup
        logger.info("Cleaning up hands-free audio stream resources...")
        try:
            recorder.stop_recording()
        except Exception:
            pass
        try:
            wake_word_detector.cleanup()
        except Exception:
            pass
        logger.info("Sherlock Voice Assistant stopped cleanly.")


if __name__ == "__main__":
    main()
