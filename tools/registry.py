"""Tool router / function-calling mapper.

Maintains a dictionary of available tools that Sherlock's brain can trigger,
parsing LLM action commands and routing them to the correct local scripts.
"""

from utils.logger import get_logger
from tools.weather import get_weather
from tools.timer import set_timer
from tools.app_opener import open_app, close_app
from tools.memory_tool import remember_fact
from tools.spotify_tool import play_spotify, pause_spotify
from tools.rss_tool import fetch_rss_feed
from tools.sports import get_live_score, get_standings

logger = get_logger(__name__)


class ToolRegistry:
    """Registry managing functions exposed to Sherlock as runnable tools."""

    def __init__(self):
        """Initializes the ToolRegistry with an empty tools map."""
        self._registry = {}

    def register(self, name: str, description: str):
        """Decorator to register a function as a tool.

        Args:
            name (str): Identifier name of the tool.
            description (str): Explanatory documentation of what the tool does.
        """
        def decorator(func):
            self._registry[name] = {
                "func": func,
                "description": description
            }
            logger.info(f"Registered tool: '{name}' - {description}")
            return func
        return decorator

    def execute(self, name: str, *args, **kwargs) -> str:
        """Executes the tool with the given name and inputs.

        Args:
            name (str): The name of the tool to execute.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            str: Stringified output results of the tool execution.
        """
        if name not in self._registry:
            logger.error(f"Tool '{name}' is not registered.")
            return f"Error: Tool '{name}' is not supported."

        tool_info = self._registry[name]
        func = tool_info["func"]
        logger.info(f"Invoking tool '{name}' with arguments: args={args}, kwargs={kwargs}")

        try:
            result = func(*args, **kwargs)
            return str(result)
        except Exception as e:
            logger.error(f"Failed to execute tool '{name}': {e}", exc_info=True)
            return f"Error executing tool '{name}': {str(e)}"

    def get_tool_definitions(self) -> list[dict]:
        """Formats the list of registered tools for LLM schemas (e.g., function calling).

        Returns:
            list[dict]: Descriptions and helper definitions of registered tools.
        """
        definitions = []
        for name, info in self._registry.items():
            definitions.append({
                "name": name,
                "description": info["description"]
            })
        return definitions


# Global Tool Registry instance
registry = ToolRegistry()

# Register core tool suite
registry.register(
    "get_live_score",
    "Queries real-time or latest match scores, game results, and match status for a specific sports team (e.g., 'Arsenal', 'Lakers', 'Real Madrid'). Use this ONLY when the user asks for scores or game results of a specific team."
)(get_live_score)

registry.register(
    "get_standings",
    "Queries current league table standings, rankings, and team points for a sports league (e.g., 'English Premier League', 'La Liga', 'NBA', 'NFL'). Use this ONLY when the user asks for league tables or standings."
)(get_standings)

registry.register(
    "get_weather",
    "Queries real-time weather conditions for a given city or location using OpenWeatherMap API."
)(get_weather)

registry.register(
    "set_timer",
    "Sets a background countdown timer for a specified number of seconds."
)(set_timer)

registry.register(
    "open_app",
    "Opens local applications (e.g., 'notepad', 'calculator', 'chrome', 'edge') via OS subprocess calls."
)(open_app)

registry.register(
    "close_app",
    "Closes or terminates a running application or browser tab."
)(close_app)

registry.register(
    "remember_fact",
    "Saves a key fact or preference about the user into persistent long-term memory."
)(remember_fact)

registry.register(
    "play_spotify",
    "Plays music, tracks, artists, or playlists on Spotify."
)(play_spotify)

registry.register(
    "pause_spotify",
    "Pauses music playback on Spotify."
)(pause_spotify)

registry.register(
    "fetch_rss_feed",
    "Fetches, parses, and summarizes recent articles, news, or blog posts from an RSS or Atom feed URL."
)(fetch_rss_feed)
