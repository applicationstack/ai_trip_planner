"""MCP server exposing a get_weather tool backed by the free Open-Meteo API."""

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Travel Tools")

WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "light rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with light hail",
    99: "thunderstorm with heavy hail",
}


@mcp.tool()
def get_weather(city: str) -> str:
    """Get today's current temperature and conditions for a city.

    Call this tool whenever a user asks about the weather for a city, or
    when planning a trip and the forecast should influence the itinerary
    (e.g. suggesting indoor activities during rain). Uses the free
    Open-Meteo API (geocoding + forecast), no API key required.

    Args:
        city: The name of the city to look up, e.g. "Paris" or "Tokyo".

    Returns:
        A short summary of today's temperature and conditions, or an
        error message if the city could not be found.
    """
    geo_response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        timeout=10,
    )
    geo_response.raise_for_status()
    geo_results = geo_response.json().get("results")

    if not geo_results:
        return f"Could not find weather for '{city}': location not found."

    location = geo_results[0]
    latitude = location["latitude"]
    longitude = location["longitude"]
    resolved_name = location.get("name", city)

    forecast_response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": "true",
        },
        timeout=10,
    )
    forecast_response.raise_for_status()
    current = forecast_response.json().get("current_weather")

    if not current:
        return f"Could not retrieve current weather for '{city}'."

    temperature = current["temperature"]
    condition = WEATHER_CODES.get(current["weathercode"], "unknown conditions")

    return f"{resolved_name}: {temperature}°C, {condition}."


if __name__ == "__main__":
    mcp.run()
