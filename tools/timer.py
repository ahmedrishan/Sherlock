"""Timer tool for Sherlock.

Provides non-blocking countdown timers that run in background threads.
"""

import time
import threading
from utils.logger import get_logger

logger = get_logger(__name__)

def set_timer(seconds: int) -> str:
    """Sets a background countdown timer for a specified number of seconds.

    Args:
        seconds (int): Time in seconds before the timer expires.

    Returns:
        str: Confirmation message.
    """
    logger.info(f"set_timer tool invoked for {seconds} seconds.")
    
    try:
        seconds = int(seconds)
    except (ValueError, TypeError):
        return "Error: Invalid number of seconds. Please provide an integer."

    def countdown():
        time.sleep(seconds)
        # Print warning to CLI when timer finishes
        print(f"\n⏰ [TIMER EXPIRED] {seconds} seconds have passed!")

    # Start timer in a background daemon thread
    timer_thread = threading.Thread(target=countdown, daemon=True)
    timer_thread.start()

    return f"Timer set for {seconds} seconds."
