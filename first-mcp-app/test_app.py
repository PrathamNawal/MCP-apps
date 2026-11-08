"""In-memory check of the MCP App tools and UI resource (needs internet)."""

import asyncio

from fastmcp import Client

from server import UI_URI, mcp


async def main():
    async with Client(mcp) as client:
        tools = {t.name: t for t in await client.list_tools()}
        print("Tools:", sorted(tools))
        print("show_weather meta:", tools["show_weather"].meta)
        res = await client.read_resource(UI_URI)
        print("UI resource:", res[0].mime_type, len(res[0].text), "chars")
        r = await client.call_tool("show_weather", {"city": "Bengaluru"})
        d = r.structured_content
        print(d["location"], d["current"], len(d["daily"]), "days", len(d["hourly"]), "hours")
        r = await client.call_tool("score_activity", {"city": "Bengaluru", "activity": "run"})
        print(r.structured_content["summary"])


asyncio.run(main())
