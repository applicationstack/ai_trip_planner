"""Client helper that launches weather_server.py over stdio and calls its
get_weather tool."""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "weather_server.py")


async def _get_weather_async(city: str) -> str:
    server_params = StdioServerParameters(command=sys.executable, args=[SERVER_SCRIPT])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_weather", {"city": city})
            return "".join(
                block.text for block in result.content if hasattr(block, "text")
            )


def get_weather(city: str) -> str:
    """Synchronous wrapper for calling the get_weather MCP tool."""
    return asyncio.run(_get_weather_async(city))
