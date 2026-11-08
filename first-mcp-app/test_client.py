"""Quick in-memory check: lists the tools and calls them without starting a server."""

import asyncio

from fastmcp import Client

from server import mcp


async def main():
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools])
        result = await client.call_tool("get_current_weather", {"city": "London"})
        print(result.data)
        result = await client.call_tool("get_forecast", {"city": "London", "days": 2})
        print(result.data)


asyncio.run(main())
