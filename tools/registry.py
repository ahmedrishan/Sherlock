"""Tool router / function-calling mapper.

Maintains a dictionary of available tools that Sherlock's brain can trigger,
parsing LLM action commands and routing them to the correct local scripts.
"""

from utils.logger import get_logger

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
