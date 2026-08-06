"""Defines system prompts, agent personas, and manages conversational memory.

Helps construct queries formatted with the assistant's persona rules
and keeps track of conversational states.
"""

SHERLOCK_BASE_PERSONA = """You are Sherlock, a highly intelligent, observant, professional, and slightly dry/witty personal AI voice assistant.

Core Behavioral Rules:
1. Tone: Sharp, observant, direct, concise, and professional with subtle dry wit.
2. Directness: Omit all sycophantic conversational filler (e.g., do NOT say "Certainly!", "Sure thing!", or "Of course!"). State answers directly.
3. Length: Keep answers strictly under 2 to 3 sentences unless the user explicitly requests detailed explanations.

Voice-First Formatting Constraints (CRITICAL for Text-to-Speech):
- NEVER output Markdown symbols or text formatting: no asterisks (*, **), code blocks (```), backticks (`), or headers (#).
- NEVER output bullet points or numbered lists. Convert all list items into short, natural, speakable prose.
- Output clean, plain text that flows smoothly when converted directly to audio by Text-to-Speech engines.
"""

SHERLOCK_SYSTEM_PROMPT = SHERLOCK_BASE_PERSONA


def get_system_instruction(facts: dict | None = None) -> str:
    """Constructs the complete system instruction for Gemini 2.5 Flash.

    Args:
        facts (dict | None): Optional key-value dictionary of long-term user facts.

    Returns:
        str: Fully hydrated system prompt string.
    """
    if not facts:
        return SHERLOCK_BASE_PERSONA

    facts_lines = ["\nKnown User Facts & Preferences:"]
    for key, val in facts.items():
        facts_lines.append(f"- {key}: {val}")

    return SHERLOCK_BASE_PERSONA + "\n" + "\n".join(facts_lines)


class ConversationMemory:
    """Handles storage and truncation of conversation history."""

    def __init__(self, max_history_len: int = 10):
        """Initializes memory with a maximum conversational window length.

        Args:
            max_history_len (int): Maximum turns (user + assistant pairs) to retain.
        """
        self.max_history_len = max_history_len
        self.history: list[dict[str, str]] = []

    def add_message(self, role: str, content: str):
        """Appends a new turn to the conversational log.

        Args:
            role (str): The role ('user' or 'assistant').
            content (str): The text message content.
        """
        self.history.append({"role": role, "content": content})

        # Enforce history limit (each turn has user & assistant messages, so length is max * 2)
        if len(self.history) > self.max_history_len * 2:
            self.history = self.history[-(self.max_history_len * 2):]

    def get_messages(self) -> list[dict[str, str]]:
        """Retrieves history in a compatible format for common APIs.

        Returns:
            list[dict[str, str]]: Conversation messages list.
        """
        return self.history

    def clear(self):
        """Wipes the history logs."""
        self.history = []
