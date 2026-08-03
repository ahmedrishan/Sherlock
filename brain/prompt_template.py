"""Defines system prompts, agent personas, and manages conversational memory.

Helps construct queries formatted with the assistant's persona rules
and keeps track of conversational states.
"""

# The primary instructions defining Sherlock's character and response limitations
SHERLOCK_SYSTEM_PROMPT = """You are Sherlock, a highly intelligent, observant, and helpful personal voice assistant.
Your style is professional, polite, yet witty and direct—inspired by a classic detective and modern digital butler.

Response Rules:
1. Be concise. Since your final responses are read aloud via Text-to-Speech, keep your response short, friendly, and speakable.
2. Avoid markdown formatting, bullet points, asterisks, and HTML inside your response.
3. Use your provided tools whenever the user requests weather information, timers, or application launching.
"""


class ConversationMemory:
    """Handles storage and truncation of conversation history."""

    def __init__(self, max_history_len: int = 10):
        """Initializes memory with a maximum conversational window length.

        Args:
            max_history_len (int): Maximum turns (user + assistant pairs) to retain.
        """
        self.max_history_len = max_history_len
        self.history = []  # List of dicts, e.g., [{"role": "user", "content": "hello"}]

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

    def get_messages(self) -> list[dict]:
        """Retrieves history in a compatible format for common APIs.

        Returns:
            list[dict]: Conversation messages list.
        """
        return self.history

    def clear(self):
        """Wipes the history logs."""
        self.history = []
