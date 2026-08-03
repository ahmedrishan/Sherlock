"""Local OS app-launching script.

Enables Sherlock to trigger host applications (e.g., Notepad, Calculator, Chrome) via subprocess calls.
"""

import subprocess
import sys
from utils.logger import get_logger

logger = get_logger(__name__)

# Mapping of common aliases to system binary names or commands
WINDOWS_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
}

def open_app(app_name: str) -> str:
    """Opens local applications (e.g., 'notepad', 'calculator', 'chrome', 'edge') via OS subprocess calls.

    Args:
        app_name (str): Friendly name of the app to launch (e.g., 'notepad', 'calculator', 'chrome').

    Returns:
        str: Result confirmation or diagnostic error log.
    """
    logger.info(f"open_app tool invoked for: '{app_name}'")
    
    if sys.platform != "win32":
        logger.warning(f"Platform is '{sys.platform}'. Local app opening is configured for win32.")
        return f"Cannot open '{app_name}': OS platform is not Windows."

    alias = app_name.lower().strip()
    target_cmd = WINDOWS_APPS.get(alias, alias)

    try:
        # Launch non-blocking background process
        subprocess.Popen(target_cmd, shell=True)
        logger.info(f"Successfully started command: {target_cmd}")
        return f"Opened {app_name} successfully."
    except Exception as e:
        logger.error(f"Failed to launch '{app_name}' using command '{target_cmd}': {e}")
        return f"Failed to open '{app_name}'. Error details: {str(e)}"

# Alias for backward compatibility
launch_app = open_app
