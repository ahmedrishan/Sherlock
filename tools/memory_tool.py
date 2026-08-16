"""Tool for persisting long-term user facts and preferences in Sherlock's SQLite database."""

from brain.memory import MemoryManager
from utils.logger import get_logger

logger = get_logger(__name__)


def remember_fact(key: str, value: str) -> str:
    """Stores a long-term user fact or preference in persistent database memory.
    Use this tool whenever the user asks you to remember something or provides personal details
    such as their name, location, occupation, or preferences.

    Args:
        key (str): The fact identifier key (e.g., 'name', 'home_city', 'favorite_color', 'user_preference').
        value (str): The value or detail to remember (e.g., 'Rishan', 'Trivandrum', 'Blue').

    Returns:
        str: Confirmation message stating the fact was stored in memory.
    """
    logger.info(f"remember_fact tool invoked: '{key}' = '{value}'")
    try:
        memory = MemoryManager()
        memory.set_fact(key, value)
        return f"Successfully saved to long-term memory: '{key}' = '{value}'."
    except Exception as e:
        logger.error(f"Error saving fact in remember_fact tool: {e}")
        return f"Failed to save fact '{key}': {e}"
