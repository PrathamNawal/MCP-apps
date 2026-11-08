# First MCP App

A basic [FastMCP](https://gofastmcp.com) (Python) server that wraps the free
[Open-Meteo](https://open-meteo.com) weather API. No API key needed.

## Tools

| Tool | Description |
|---|---|
| `get_current_weather(city)` | Current temperature, humidity, wind and weather code |
| `get_forecast(city, days=3)` | Daily min/max temperature and precipitation (1-16 days) |
| `show_weather(city)` | **MCP App**: interactive card with current conditions, 7-day outlook, hourly rain chance, °C/°F toggle |
| `score_activity(city, activity, date?)` | Scores each hour for run/walk/cycling/cricket/picnic/photography/commute and picks the best window (also called from the app's planner) |

The app UI lives in `ui/weather.html` and is served as the `ui://weather/app.html` resource
(MCP Apps extension). Hosts without MCP Apps support just get the structured data.

## Run

```bash
uv sync
uv run python server.py   # serves http://127.0.0.1:8000/mcp
```

## Connect

Claude Code:

```bash
claude mcp add --transport http weather http://127.0.0.1:8000/mcp
```

## Test

```bash
uv run python test_client.py   # calls the tools in-memory (needs internet)
uv run python test_app.py      # checks the app tools + UI resource
```

## Deploy

The server reads `PORT` (and optional `HOST`) so it runs on any container host.
A `Dockerfile` and a Render blueprint (`render.yaml`) are included.

1. Push this repo to GitHub.
2. Render: New -> Blueprint -> pick this repo (root directory `first-mcp-app`).
   Any other Docker host (Fly.io, Railway, Cloud Run) works the same way.
3. Your MCP URL is `https://<your-service>.onrender.com/mcp`.
4. In claude.ai: Settings -> Connectors -> Add custom connector -> paste the URL.

Note: the server has no authentication, so anyone with the URL can call it.
