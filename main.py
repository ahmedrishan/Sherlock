"""Application entry point and orchestration loop for Sherlock.

Acts as the central coordinator initializing inputs, audio queues,
the cognitive brain (LLM client), the tool registry, and the TTS feedback.
"""

import sys
import io
import os
import re
# Third-party audio and voice synthesis dependencies
import pygame
from elevenlabs.client import ElevenLabs

import config
from utils.logger import get_logger

# Import core modules
from core.audio_recorder import AudioRecorder
from core.wakeword import WakeWordDetector
from core.stt import SpeechToText
from core.tts import TextToSpeech

# Import brain modules
from brain.llm_client import LLMClient
from brain.prompt_template import ConversationMemory, SHERLOCK_SYSTEM_PROMPT

# Import tools modules
from tools.registry import ToolRegistry
from tools.weather import get_weather
from tools.timer import set_timer
from tools.app_opener import launch_app as open_app

logger = get_logger(__name__)

# Initialize pygame mixer safely
try:
    pygame.mixer.init()
    pygame_mixer_initialized = True
    logger.info("Pygame mixer initialized successfully.")
except Exception as e:
    logger.warning(f"Could not initialize pygame mixer: {e}. Audio playback will be skipped.")
    pygame_mixer_initialized = False

# Initialize ElevenLabs client
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY", config.ELEVENLABS_API_KEY))

def speak_text(text: str):
    """Converts the given text to speech using ElevenLabs and plays it via Pygame.

    Args:
        text (str): The text message to speak.
    """
    if not text or not text.strip():
        return

    # Clean up response for speakability (remove formatting characters)
    clean_text = re.sub(r"[*_`#\-\[\]]", "", text)
    
    # Check if API key is present
    api_key = os.getenv("ELEVENLABS_API_KEY", config.ELEVENLABS_API_KEY)
    if not api_key:
        logger.warning(f"[TTS Bypass] (No ELEVENLABS_API_KEY set) Sherlock would say: '{clean_text}'")
        return

    if not pygame_mixer_initialized:
        logger.warning(f"[TTS Bypass] (Pygame mixer not active) Sherlock would say: '{clean_text}'")
        return

    try:
        logger.info(f"Generating voice for: '{clean_text}'")
        # Generate MP3 stream
        audio_generator = eleven_client.generate(
            text=clean_text,
            voice="Rachel",
            model="eleven_turbo_v2_5"
        )
        audio_bytes = b"".join(audio_generator)
        sound_buffer = io.BytesIO(audio_bytes)

        # Play via Pygame
        pygame.mixer.music.load(sound_buffer)
        pygame.mixer.music.play()
        
        # Busy-wait loop until audio completes
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
    except Exception as e:
        print(f"⚠️ [TTS Error]: {e}")

def parse_action(text: str):
    """Parses 'Action: [tool_name]' and 'Action Input: [arg]' from LLM output.

    Args:
        text (str): Raw LLM response.

    Returns:
        tuple[str, str] | None: Tool name and input if found, otherwise None.
    """
    action_match = re.search(r"Action:\s*([a-zA-Z0-9_-]+)", text)
    action_input_match = re.search(r"Action Input:\s*(.+)", text)
    if action_match and action_input_match:
        tool_name = action_match.group(1).strip()
        tool_arg = action_input_match.group(1).strip().strip('"').strip("'")
        return tool_name, tool_arg
    return None

def parse_final_answer(text: str):
    """Parses 'Final Answer: [response]' from LLM output.

    Args:
        text (str): Raw LLM response.

    Returns:
        str | None: The parsed final answer text if found, otherwise None.
    """
    final_match = re.search(r"Final Answer:\s*(.+)", text, re.DOTALL)
    if final_match:
        return final_match.group(1).strip()
    return None

def run_react_loop(user_query: str, brain: LLMClient, memory: ConversationMemory, tools: ToolRegistry) -> str:
    """Executes the ReAct reasoning loop (Thought -> Action -> Observation -> Final Answer).

    Args:
        user_query (str): The initial query from the user.
        brain (LLMClient): The LLM client wrapper.
        memory (ConversationMemory): Conversational history memory.
        tools (ToolRegistry): Registered system tools.

    Returns:
        str: The final natural language response from the agent.
    """
    active_prompt = f"User Query: {user_query}"
    max_steps = 5

    for step in range(max_steps):
        logger.info(f"ReAct Loop Step {step + 1}...")
        response_text = brain.generate_response(
            user_query=active_prompt,
            system_instruction=SHERLOCK_SYSTEM_PROMPT,
            history=memory.get_messages()
        )
        
        # Check for tool call
        action_info = parse_action(response_text)
        if action_info:
            tool_name, tool_arg = action_info
            print(f"🤖 [Thought]: System decides to execute tool '{tool_name}' with argument '{tool_arg}'")
            
            # Execute tool
            observation = tools.execute(tool_name, tool_arg)
            print(f"🔍 [Observation]: {observation}")
            
            # Append reasoning path and observation back to the prompt context
            active_prompt += f"\n{response_text}\nObservation: {observation}"
        else:
            # Check for final answer
            final_answer = parse_final_answer(response_text)
            if final_answer:
                return final_answer
            
            # Fallback if no specific Final Answer token is output, but no action was requested either
            if "Action:" not in response_text:
                return response_text.strip()
                
            active_prompt += f"\n{response_text}\nObservation: Please specify a valid tool name or provide your Final Answer."

    return "I apologize, but I could not resolve that query within my reasoning limit."

def main():
    """Initializes and runs the main orchestrator loop."""
    logger.info("Initializing Sherlock Voice Assistant...")

    # Instantiate skeletons and modules
    try:
        recorder = AudioRecorder()
        wakeword = WakeWordDetector()
        stt = SpeechToText()
        tts = TextToSpeech()  # Modular placeholder
        brain = LLMClient()
        memory = ConversationMemory()
        
        # Initialize and register tools
        tools = ToolRegistry()
        
        @tools.register("get_weather", "Retrieves current weather condition for a city. Args: location (str)")
        def tool_weather(location: str) -> str:
            return get_weather(location)
            
        @tools.register("set_timer", "Sets a background countdown timer for N seconds. Args: seconds (int)")
        def tool_timer(seconds: int) -> str:
            return set_timer(seconds)
            
        @tools.register("open_app", "Opens/launches a local Windows application. Args: app_name (str)")
        def tool_open_app(app_name: str) -> str:
            return open_app(app_name)

        logger.info("All modules imported and initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize Sherlock components: {e}", exc_info=True)
        sys.exit(1)

    print("\n==================================================")
    print("         Sherlock Voice Assistant (Mini Jarvis)")
    print("              Status: ACTIVE (ReAct Loop)")
    print("==================================================")
    print(f"LLM Provider:  {config.DEFAULT_LLM_PROVIDER}")
    print(f"TTS Provider:  {config.TTS_PROVIDER} (Pygame + ElevenLabs)")
    print(f"STT Model:     {config.STT_MODEL_SIZE} ({config.STT_DEVICE})")
    print("==================================================")
    print("Sherlock is ready. Start typing below (type 'exit' to quit).")
    print("==================================================\n")

    # CLI Loop
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
                
            if user_input.lower() in ["exit", "quit", "bye"]:
                goodbye_msg = "Goodbye. Have a pleasant day."
                print(f"Sherlock: {goodbye_msg}")
                speak_text(goodbye_msg)
                break

            # Resolve query using ReAct reasoning loop
            final_response = run_react_loop(user_input, brain, memory, tools)
            
            # Print response
            print(f"Sherlock: {final_response}")
            
            # Text-To-Speech playback
            speak_text(final_response)

            # Record conversation history
            memory.add_message("user", user_input)
            memory.add_message("assistant", final_response)

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
