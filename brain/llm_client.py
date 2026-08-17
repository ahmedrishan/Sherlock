"""LLM Client orchestrator for Sherlock.

Integrates with Gemini, OpenAI, or Anthropic, providing unified text completion
and support for system prompts and conversational history.
"""

import config
from utils.logger import get_logger

logger = get_logger(__name__)

class LLMClient:
    """Manages connections to language model APIs."""

    def __init__(self):
        """Initializes the LLM client configuration."""
        logger.info("Initializing LLMClient...")
        self.provider = config.DEFAULT_LLM_PROVIDER
        self.client = None
        self._initialize_provider()

    def _initialize_provider(self):
        """Sets up specific API clients depending on configuration."""
        if self.provider == "gemini":
            logger.info("Using Gemini API provider.")
            if not config.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY is not configured in settings.")
                return
            try:
                from google import genai
                self.client = genai.Client(api_key=config.GEMINI_API_KEY)
                logger.info("Successfully initialized Gemini GenAI Client.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
        elif self.provider == "openai":
            logger.info("Using OpenAI API provider.")
            # TODO: Initialize openai client
        elif self.provider == "anthropic":
            logger.info("Using Anthropic API provider.")
            # TODO: Initialize anthropic client
        else:
            logger.warning(f"Unknown provider '{self.provider}'. Falling back to Gemini.")
            self.provider = "gemini"

    def generate_response(self, user_query: str, system_instruction: str, history: list[dict] = None) -> str:
        """Generates a text response from the configured LLM.

        Args:
            user_query (str): The current user query or transcription.
            system_instruction (str): Persona rules and behavior instructions.
            history (list[dict], optional): Conversation history. Defaults to None.

        Returns:
            str: The textual response text from the LLM.
        """
        logger.info(f"Generating response from {self.provider} model...")
        
        if self.provider == "gemini":
            return self._query_gemini(user_query, system_instruction, history)
        elif self.provider == "openai":
            return self._query_openai(user_query, system_instruction, history)
        elif self.provider == "anthropic":
            return self._query_anthropic(user_query, system_instruction, history)
        
        return "I apologize, but I could not compute a response."

    def _query_gemini(self, query: str, system: str, history: list) -> str:
        if not self.client:
            logger.warning("Gemini client not initialized. Querying in stub mode.")
            return "[Gemini Stub] Understood, how may I assist you?"
        try:
            from google.genai import types
            
            # Format chat history
            contents = []
            if history:
                for turn in history:
                    role = "user" if turn["role"] == "user" else "model"
                    contents.append(types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=turn["content"])]
                    ))
            
            # Append current query
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=query)]
            ))

            response = self.client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=config.TEMPERATURE,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            return f"Error querying Gemini API: {str(e)}"

    def _query_openai(self, query: str, system: str, history: list) -> str:
        # TODO: Implement OpenAI generation API call
        return "[OpenAI Stub] Understood, how may I assist you?"

    def _query_anthropic(self, query: str, system: str, history: list) -> str:
        # TODO: Implement Anthropic generation API call
        return "[Anthropic Stub] Understood, how may I assist you?"
