# First MCP App

A basic [FastMCP](https://gofastmcp.com) (Python) server that wraps the free
[Open-Meteo](https://open-meteo.com) weather API. No API key needed.

## Tools

| Tool | Description |
|---|---|
| `get_current_weather(city)` | Current temperature, humidity, wind and weather code |
| `get_forecast(city, days=3)` | Daily min/max temperature and precipitation (1-16 days) |

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
```
