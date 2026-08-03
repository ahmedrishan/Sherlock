"""Application entry point and orchestration loop for Sherlock (Mini Jarvis).

Acts as the central coordinator initializing inputs, audio queues,
the cognitive brain (Gemini GenAI ReAct Engine), tools, and TTS feedback.
"""

import io
import os
import re
import sys
import threading
from typing import Dict, Any, Callable

import pygame
from google import genai
from google.genai import types
from elevenlabs.client import ElevenLabs

import config
from utils.logger import get_logger

# Import core hardware & voice modules
from core.audio_recorder import AudioRecorder
from core.stt import SpeechToText
from core.tts import TextToSpeech

# Import brain & prompt templates
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
            temperature=0.2,  # Low variance for deterministic tool routing (Toolformer)
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
    """Initializes Sherlock CLI assistant and runs the main ReAct interaction loop."""
    logger.info("Initializing Sherlock Voice Assistant (Mini Jarvis)...")

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

    # Initialize audio hardware, STT, and TTS modules
    recorder = AudioRecorder()
    stt = SpeechToText()
    tts = get_tts_engine()

    print("\n==================================================")
    print("         Sherlock Voice Assistant (Mini Jarvis)")
    print("           Brain: Gemini ReAct Engine (2.5-Flash)")
    print("==================================================")
    print(f"LLM Provider:  Gemini GenAI ({model_name})")
    print(f"TTS Provider:  {config.TTS_PROVIDER} (Pygame + ElevenLabs)")
    print(f"STT Engine:    faster-whisper ({config.STT_MODEL_SIZE})")
    print("Tools Loaded:  get_weather, set_timer, open_app")
    print("==================================================")
    print("Sherlock is ready. Type your prompt or enter 'r' / 'voice' for Push-to-Talk voice input (type 'exit' to quit).")
    print("==================================================\n")

    # Interactive CLI Loop
    while True:
        try:
            user_input = input("You (text or 'r' for voice): ").strip()
            if not user_input:
                continue

            # Push-to-Talk Voice Input mode
            if user_input.lower() in ["r", "rec", "voice", "speak"]:
                try:
                    audio_path = recorder.record_until_keypress()
                    user_input = stt.transcribe(audio_path).strip()
                    if not user_input:
                        print("Sherlock: I didn't catch any speech. Please try again.")
                        continue
                    print(f"You (Voice STT): {user_input}")
                except Exception as rec_err:
                    logger.error(f"Voice recording / STT failed: {rec_err}")
                    print(f"⚠️ [STT Error]: {rec_err}")
                    continue

            # Exit command
            if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                goodbye_msg = "Goodbye. Have a pleasant day."
                print(f"Sherlock: {goodbye_msg}")
                speak_text(goodbye_msg)
                break

            # Execute ReAct decision engine
            final_response = run_react_loop(chat_session, user_input)
            
            # Print answer & trigger TTS playback
            print(f"Sherlock: {final_response}")
            speak_text(final_response)

        except KeyboardInterrupt:
            goodbye_msg = "Goodbye. Have a pleasant day."
            print(f"\nSherlock: {goodbye_msg}")
            speak_text(goodbye_msg)
            break
        except Exception as e:
            logger.error(f"Error in CLI interaction loop: {e}", exc_info=True)
            print(f"⚠️ [System Error]: {e}")


if __name__ == "__main__":
    main()

