"""Application entry point and orchestration loop for Sherlock.

Acts as the central coordinator initializing hardware inputs, audio queues,
the cognitive brain (LLM client), and the tool registry.
"""

import sys
import config
from utils.logger import get_logger

# Import core modules to verify import paths
from core.audio_recorder import AudioRecorder
from core.wakeword import WakeWordDetector
from core.stt import SpeechToText
from core.tts import TextToSpeech

# Import brain modules
from brain.llm_client import LLMClient
from brain.prompt_template import ConversationMemory

# Import tools module
from tools.registry import ToolRegistry

logger = get_logger(__name__)

def main():
    """Initializes and runs the main orchestrator loop."""
    logger.info("Initializing Sherlock Voice Assistant skeleton...")

    # Instantiate skeletons to verify structure and paths
    try:
        recorder = AudioRecorder()
        wakeword = WakeWordDetector()
        stt = SpeechToText()
        tts = TextToSpeech()
        brain = LLMClient()
        memory = ConversationMemory()
        tools = ToolRegistry()
        
        logger.info("All modules imported and initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize Sherlock components: {e}", exc_info=True)
        sys.exit(1)

    print("\n==================================================")
    print("         Sherlock Voice Assistant")
    print("              Status: ACTIVE")
    print("==================================================")
    print(f"LLM Provider:  {config.DEFAULT_LLM_PROVIDER}")
    print(f"TTS Provider:  {config.TTS_PROVIDER}")
    print(f"STT Model:     {config.STT_MODEL_SIZE} ({config.STT_DEVICE})")
    print("==================================================")
    print("Sherlock is ready. Phased builds can start here.")
    print("==================================================\n")

if __name__ == "__main__":
    main()
