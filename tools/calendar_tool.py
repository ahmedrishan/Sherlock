"""Calendar integration tool for Sherlock.

Exposes operations to read and write events to local calendars or Google Calendar.
"""

from utils.logger import get_logger

logger = get_logger(__name__)

def get_upcoming_events(max_events: int = 5) -> str:
    """Fetches upcoming events from the active calendar.

    Args:
        max_events (int): Limit on the number of retrieved items. Defaults to 5.

    Returns:
        str: A listing description of calendar items.
    """
    logger.info(f"get_upcoming_events invoked with max_events={max_events}")
    # TODO: Connect to Google Calendar API / CalDAV client
    return "No upcoming events found on your calendar."

def add_event(summary: str, start_time: str, end_time: str = None) -> str:
    """Creates a new entry on the active calendar.

    Args:
        summary (str): Title or topic of the event.
        start_time (str): Iso-formatted start timestamp.
        end_time (str, optional): Iso-formatted end timestamp.

    Returns:
        str: Outcome confirmation message.
    """
    logger.info(f"add_event tool invoked: '{summary}' starting at {start_time}")
    # TODO: Connect to Google Calendar API / CalDAV client and insert
    return f"Successfully added event '{summary}' to your calendar (Placeholder)."
