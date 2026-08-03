"""Weather API tool for Sherlock.

Provides functionalities to retrieve current conditions and forecasts for locations worldwide.
"""

import config
from utils.logger import get_logger

logger = get_logger(__name__)

def get_weather(location: str) -> str:
    """Queries current weather conditions for a given city or location.

    Args:
        location (str): The name of the city or location (e.g., 'London', 'San Francisco').

    Returns:
        str: Weather details description or status message.
    """
    logger.info(f"get_weather tool invoked for: '{location}'")
    api_key = config.WEATHER_API_KEY

    if not api_key:
        logger.warning("WEATHER_API_KEY is not configured in settings. Returning mock data.")
        return f"Mock weather for {location}: Sunny, 21°C (70°F), humidity at 45%."

    # TODO: Implement request to OpenWeatherMap or other weather api
    # url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
    # response = requests.get(url).json()
    
    return f"Weather information for {location} is currently unavailable (API integration pending)."
