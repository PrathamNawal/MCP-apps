"""A basic MCP server that wraps the free Open-Meteo weather API (no API key needed)."""

import os

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("Weather")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


async def _get(url: str, params: dict) -> dict:
    """GET a JSON endpoint, turning network/API failures into clear tool errors."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        raise ToolError(f"Open-Meteo request failed: {e}") from e


async def _geocode(city: str) -> dict:
    data = await _get(GEOCODE_URL, {"name": city, "count": 1})
    results = data.get("results")
    if not results:
        raise ToolError(f"Could not find a location named '{city}'.")
    return results[0]


@mcp.tool
async def get_current_weather(city: str) -> dict:
    """Get the current weather for a city (e.g. "Paris" or "Mumbai")."""
    place = await _geocode(city)
    data = await _get(
        FORECAST_URL,
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        },
    )
    return {
        "location": f"{place['name']}, {place.get('country', '')}".strip(", "),
        "current": data["current"],
        "units": data["current_units"],
    }


@mcp.tool
async def get_forecast(city: str, days: int = 3) -> dict:
    """Get a daily forecast (1-16 days) for a city: min/max temperature and precipitation."""
    if not 1 <= days <= 16:
        raise ToolError("days must be between 1 and 16.")
    place = await _geocode(city)
    data = await _get(
        FORECAST_URL,
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "forecast_days": days,
            "timezone": "auto",
        },
    )
    return {
        "location": f"{place['name']}, {place.get('country', '')}".strip(", "),
        "daily": data["daily"],
        "units": data["daily_units"],
    }


if __name__ == "__main__":
    # Hosts like Render/Fly/Railway/Cloud Run set PORT and need 0.0.0.0.
    # Locally this defaults to 127.0.0.1:8000.
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    mcp.run(transport="http", host=host, port=port)
