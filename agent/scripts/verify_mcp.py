import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = r"D:\insight-pilot\agent\mcp_server.py"


async def main():
    params = StdioServerParameters(command=sys.executable, args=[SERVER], cwd=r"D:\insight-pilot\agent")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]
            print("tools:", names)
            result = await session.call_tool("get_enum_values", {})
            text = result.content[0].text if result.content else ""
            print("callOk:", bool(text) and "orders.status" in text)


if __name__ == "__main__":
    asyncio.run(main())
