"""A basic MCP server that wraps the free Open-Meteo weather API (no API key needed)."""

import os
from datetime import date as _date
from pathlib import Path

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("Weather")

UI_URI = "ui://weather/app.html"
UI_MIME = "text/html;profile=mcp-app"
UI_HTML = Path(__file__).parent / "ui" / "weather.html"

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
    """Raw current-weather data for a city, as plain numbers. Only use this when you need the data
    for calculations; for any user-facing weather question call `show_weather` instead, which
    shows an interactive card."""
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
    """Raw daily forecast numbers (1-16 days) for a city. Only use this for forecasts longer than
    7 days or when you need the data for calculations; for any user-facing weather or forecast
    question (including "next 7 days") call `show_weather` instead, which shows an interactive card."""
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


# ---------------------------------------------------------------- MCP App ---

# activity -> (ideal temp low, ideal temp high, max comfortable wind km/h, rain tolerance 0-1)
ACTIVITIES = {
    "run": (8, 20, 25, 0.5),
    "walk": (10, 27, 30, 0.5),
    "cycling": (10, 26, 18, 0.4),
    "cricket": (18, 32, 30, 0.1),
    "picnic": (18, 29, 20, 0.0),
    "photography": (5, 30, 35, 0.6),
    "commute": (5, 35, 40, 0.8),
}
# sensible local hours (inclusive) to consider for each activity
ACTIVITY_HOURS = {
    "run": (5, 21), "walk": (6, 21), "cycling": (5, 19), "cricket": (7, 18),
    "picnic": (9, 18), "photography": (5, 19), "commute": (6, 21),
}


def _score_hour(activity: str, temp: float, wind: float, prob: float, mm: float, code: int) -> int:
    lo, hi, max_wind, rain_tol = ACTIVITIES[activity]
    score = 100.0
    if temp < lo:
        score -= (lo - temp) * 4
    elif temp > hi:
        score -= (temp - hi) * 5
    if wind > max_wind:
        score -= (wind - max_wind) * 2
    score -= prob * (1 - rain_tol) * 0.7 + min(mm, 5) * 8 * (1 - rain_tol)
    if code >= 95:  # thunderstorm
        score -= 60
    return max(0, min(100, round(score)))


async def _bundle(city: str) -> dict:
    place = await _geocode(city)
    data = await _get(
        FORECAST_URL,
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "hourly": "temperature_2m,precipitation_probability,precipitation,wind_speed_10m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum",
            "forecast_days": 7,
            "timezone": "auto",
        },
    )
    cur, h, d = data["current"], data["hourly"], data["daily"]
    return {
        "city": city,
        "location": f"{place['name']}, {place.get('country', '')}".strip(", "),
        "current": {
            "temperature": cur["temperature_2m"],
            "humidity": cur["relative_humidity_2m"],
            "wind_speed": cur["wind_speed_10m"],
            "weather_code": cur["weather_code"],
        },
        "daily": [
            {"date": d["time"][i], "weather_code": d["weather_code"][i], "max": d["temperature_2m_max"][i],
             "min": d["temperature_2m_min"][i], "precip": d["precipitation_sum"][i]}
            for i in range(len(d["time"]))
        ],
        "hourly": [
            {"time": h["time"][i], "temperature": h["temperature_2m"][i],
             "precip_prob": h["precipitation_probability"][i] or 0, "precip": h["precipitation"][i] or 0,
             "wind": h["wind_speed_10m"][i], "weather_code": h["weather_code"][i]}
            for i in range(len(h["time"]))
        ],
    }


@mcp.resource(UI_URI, mime_type=UI_MIME, meta={"ui": {"prefersBorder": False}})
def weather_app_ui() -> str:
    """Interactive weather card with a 7-day outlook and an activity planner."""
    return UI_HTML.read_text(encoding="utf-8")


@mcp.tool(app={"resourceUri": UI_URI})
async def show_weather(city: str) -> dict:
    """DEFAULT tool for any weather question (current conditions, today, this week, "forecast",
    "next 7 days", rain, temperature). Shows an interactive weather card for a city with current
    conditions, a 7-day outlook, hourly rain chances and an activity planner. Call this first
    instead of get_current_weather or get_forecast, and keep your text reply to one short sentence
    since the card already shows the details."""
    return await _bundle(city)


@mcp.tool(app={"resourceUri": UI_URI})
async def score_activity(city: str, activity: str, date: str | None = None) -> dict:
    """Find the best time of day for an outdoor activity (run, walk, cycling, cricket, picnic,
    photography, commute) in a city. `date` is YYYY-MM-DD (defaults to today); only sensible hours for the activity are scored."""
    activity = activity.lower().strip()
    if activity not in ACTIVITIES:
        raise ToolError(f"Unknown activity '{activity}'. Choose from: {', '.join(ACTIVITIES)}.")
    b = await _bundle(city)
    day = date or b["daily"][0]["date"]
    try:
        _date.fromisoformat(day)
    except ValueError as e:
        raise ToolError("date must be YYYY-MM-DD.") from e
    first, last = ACTIVITY_HOURS[activity]
    hours = [h for h in b["hourly"] if h["time"][:10] == day and first <= int(h["time"][11:13]) <= last]
    if not hours:
        raise ToolError(f"No forecast for {day}; pick a date within the next 7 days.")
    for h in hours:
        h["score"] = _score_hour(activity, h["temperature"], h["wind"], h["precip_prob"], h["precip"], h["weather_code"])
    # best 2-hour window (or single hour if only one is available)
    n = 2 if len(hours) >= 2 else 1
    wins = [(sum(x["score"] for x in hours[i:i + n]) / n, i) for i in range(len(hours) - n + 1)]
    avg, i = max(wins)
    start, end = hours[i]["time"], hours[i + n - 1]["time"]
    if avg >= 70:
        verdict = "Good conditions"
    elif avg >= 45:
        verdict = "Okay, with caveats"
    else:
        verdict = "Not a great day for it"
    return {
        "city": b["city"], "location": b["location"], "activity": activity, "date": day,
        "hours": hours,
        "best": {"start": start, "end": end, "score": round(avg)},
        "summary": f"{verdict}: best {activity} window is {start[11:16]}-{end[11:13]}:59 "
                   f"(score {round(avg)}/100, ~{round(hours[i]['temperature'])}°C, "
                   f"{hours[i]['precip_prob']}% rain chance).",
    }


if __name__ == "__main__":
    # Hosts like Render/Fly/Railway/Cloud Run set PORT and need 0.0.0.0.
    # Locally this defaults to 127.0.0.1:8000.
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    mcp.run(transport="http", host=host, port=port)
