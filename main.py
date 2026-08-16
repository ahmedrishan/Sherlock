"""Application entry point and continuous hands-free execution loop for Sherlock (Mini Jarvis).

Pipeline Architecture:
  WakeWordDetector (openWakeWord "sherlock")
  -> AudioRecorder (Low-Latency VAD 0.9s timeout)
  -> SpeechToText (faster-whisper)
  -> Gemini GenAI ReAct Brain (3.6-Flash + Memory & Function Calling)
  -> TextToSpeech Engine (ElevenLabs / Pygame)
"""

import os
import random
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

# Import brain modules (memory & prompt template)
from brain.memory import MemoryManager
from brain.prompt_template import get_system_instruction

# Import baseline system tools
from tools.weather import get_weather
from tools.timer import set_timer
from tools.app_opener import open_app, close_app
from tools.memory_tool import remember_fact
from tools.spotify_tool import play_spotify, pause_spotify

logger = get_logger(__name__)

# Register baseline tool mapping
TOOLS_LIST = [get_weather, set_timer, open_app, close_app, remember_fact, play_spotify, pause_spotify]
TOOL_MAP: Dict[str, Callable] = {
    "get_weather": get_weather,
    "set_timer": set_timer,
    "open_app": open_app,
    "close_app": close_app,
    "remember_fact": remember_fact,
    "play_spotify": play_spotify,
    "pause_spotify": pause_spotify,
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


def get_wake_greeting(user_name: str | None = None) -> str:
    """Returns a randomized Sherlock greeting upon wake word detection."""
    name_suffix = f", {user_name}" if user_name else ""
    greetings = [
        f"At your service{name_suffix}.",
        f"Yes{name_suffix}? How may I assist you?",
        "Listening. What do you need?",
        f"Welcome back{name_suffix}.",
        f"I am here boss",
        f"Ready when you are{name_suffix}.",
        f"Good day{name_suffix}. I am listening.",
    ]
    return random.choice(greetings)


def create_chat_session(client: genai.Client, model_name: str, facts: dict | None = None):
    """Creates a Gemini chat session hydrated with persona rules and long-term user facts.

    Args:
        client (genai.Client): Initialized GenAI client instance.
        model_name (str): Gemini model identifier (e.g. 'gemini-2.5-flash').
        facts (dict | None): Optional dictionary of long-term user facts.

    Returns:
        Chat: GenAI chat session object.
    """
    system_instruction = get_system_instruction(facts)
    return client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
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
            logger.info(f"[ReAct Step {step}] Tool requested: '{func_name}' with args: {func_args}")
            print(f"[ReAct Step {step}] Tool: '{func_name}' | Args: {func_args}")

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
            logger.info(f"[ReAct Step {step}] Observation returned: {observation}")
            print(f"[ReAct Step {step}] Observation: {observation}")

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

    model_name = getattr(config, "GEMINI_MODEL", "gemini-3.6-flash")

    # Instantiate SQLite Memory Manager and fetch long-term user facts
    memory = MemoryManager()
    user_facts = memory.get_all_facts()
    logger.info(f"Loaded {len(user_facts)} long-term user facts from memory.")

    try:
        client = genai.Client(api_key=gemini_key)
        chat_session = create_chat_session(client, model_name=model_name, facts=user_facts)
        logger.info(f"Gemini GenAI client initialized with model '{model_name}'.")
    except Exception as e:
        logger.critical(f"Failed to initialize Gemini GenAI client: {e}", exc_info=True)
        sys.exit(1)

    # 1. Instantiate Pipeline Hardware & Speech Modules
    logger.info("Instantiating pipeline hardware & speech modules...")
    target_word = getattr(config, "WAKE_WORD_MODEL", "sherlock")
    backup_word = getattr(config, "BACKUP_WAKE_WORD_MODEL", "hey_jarvis")
    threshold = getattr(config, "WAKE_WORD_THRESHOLD", 0.25)
    wake_word_detector = WakeWordDetector(target_word=target_word, backup_word=backup_word, threshold=threshold)
    recorder = AudioRecorder(sample_rate=16000)
    stt_engine = SpeechToText()
    tts_engine = get_tts_engine()

    print("\n==================================================")
    print("         Sherlock Voice Assistant (Mini Jarvis)")
    print("           Hands-Free Always-Listening Mode")
    print("==================================================")
    print(f"Wake Word:    openWakeWord ('{target_word}' | Backup: '{backup_word}')")
    print(f"VAD Timeout:  0.9s trailing silence cutoff")
    print(f"STT Engine:   faster-whisper ({config.STT_MODEL_SIZE})")
    print(f"Brain LLM:    Gemini GenAI ({model_name})")
    print(f"Memory DB:    data/memory.db ({len(user_facts)} facts loaded)")
    print(f"TTS Provider: {config.TTS_PROVIDER} (ElevenLabs / Pygame)")
    print("==================================================")
    print(f"Sherlock is ready and listening for '{target_word}' / '{backup_word}' (Press Ctrl+C to stop)...")
    print("==================================================\n")

    # 2. Hands-Free Execution Loop (Active Conversation Window Mode)
    active_timeout = getattr(config, "ACTIVE_CONVERSATION_TIMEOUT", 15.0)
    in_active_session = False

    try:
        while True:
            # a. If not in active session, wait for wake word trigger
            if not in_active_session:
                triggered = wake_word_detector.listen_for_wake_word()
                if not triggered:
                    continue
                in_active_session = True
                greeting = get_wake_greeting(user_facts.get("name"))
                print(f"\n⚡ Wake word '{target_word}' detected!")
                print(f"Sherlock: {greeting}")
                speak_text(greeting)
            else:
                print(f"\n💬 Sherlock active ({int(active_timeout)}s window)... Listening for follow-up command...")

            # b. Record command using VAD with active inactivity timeout
            wav_path = recorder.record_command_with_vad(
                silence_duration=0.9,
                speech_threshold=500.0,
                inactivity_timeout=active_timeout if in_active_session else None,
            )

            # c. Handle inactivity timeout / empty recording
            if not wav_path or not os.path.exists(wav_path):
                if in_active_session:
                    print(f"😴 {int(active_timeout)}s inactivity timeout reached. Sherlock returning to sleep mode.")
                    print(f"sleeping... Listening for wake word ('{target_word}')...\n")
                    in_active_session = False
                continue

            # d. Transcribe audio input via faster-whisper
            try:
                user_text = stt_engine.transcribe(wav_path).strip()
            except Exception as stt_err:
                logger.error(f"STT transcription error: {stt_err}")
                print(f"⚠️ [STT Error]: {stt_err}")
                print(f"sleeping... Listening for wake word ('{target_word}')...\n")
                in_active_session = False
                continue

            # e. Handle empty transcription
            if not user_text:
                print("Sherlock: I didn't catch any words.")
                continue

            # f. Check for explicit exit/sleep phrases
            if any(term in user_text.lower() for term in ["stop listening", "go to sleep", "goodbye", "sleep"]):
                print(f"You (Voice): {user_text}")
                print("Sherlock: Goodbye! Going to sleep.")
                speak_text("Goodbye! Going to sleep.")
                in_active_session = False
                print(f"sleeping... Listening for wake word ('{target_word}')...\n")
                continue

            print(f"You (Voice): {user_text}")
            memory.add_turn("user", user_text)

            # g. Execute ReAct brain loop
            try:
                final_response = run_react_loop(chat_session, user_text)
            except Exception as brain_err:
                err_msg = str(brain_err)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    logger.warning(f"Gemini API daily/free-tier quota reached: {brain_err}")
                    final_response = "I have temporarily reached my Gemini API free tier request limit. Please wait a moment before trying again."
                else:
                    logger.error(f"ReAct decision engine error: {brain_err}")
                    final_response = "I encountered an issue processing your request."

            # h. Record assistant turn & speak response back to user out loud
            memory.add_turn("assistant", final_response)
            print(f"Sherlock: {final_response}")
            speak_text(final_response)

            # i. Keep active conversation window refreshed
            print(f"⚡ Response completed. Sherlock remains active for {int(active_timeout)}s follow-up...\n")

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
