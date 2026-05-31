"""Entrypoint for running the MCP server via stdio transport.

Usage:
    python -m app.mcp_server
"""

import asyncio
import logging

from mcp.server.stdio import stdio_server

from app.mcp_server.server import create_server

logging.basicConfig(level=logging.INFO)


async def main():
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
