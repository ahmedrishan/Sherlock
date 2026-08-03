"""Centralized configuration module for Sherlock.

Loads environment variables from the `.env` file and defines application settings,
paths, api keys, and model parameters.
"""

import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    # Load environment variables from .env
    load_dotenv()
except ImportError:
    # Fallback to local environment variables if python-dotenv is not installed
    pass


# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")


# LLM / Brain Settings
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "gemini").lower()  # gemini, openai, anthropic
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

# Audio Recording Settings
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
AUDIO_CHUNK_SIZE = int(os.getenv("AUDIO_CHUNK_SIZE", "1024"))

# Wake Word Settings (Picovoice Porcupine)
WAKE_WORD_MODEL_PATH = os.getenv("WAKE_WORD_MODEL_PATH", "")

# Speech to Text Settings (faster-whisper)
STT_MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "base")
STT_DEVICE = os.getenv("STT_DEVICE", "cpu")  # cpu or cuda

# Text to Speech Settings
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "elevenlabs")  # elevenlabs, piper, local

# Logging Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
