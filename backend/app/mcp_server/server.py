"""MCP Server for Cold Email CRM.

Exposes CRM operations as MCP tools for use by Claude Code and other MCP clients.
Each tool reuses the existing service layer — no API logic is duplicated.
"""

import logging

from mcp.server import Server
from mcp.types import Tool, TextContent

from app.mcp_server.tools.campaigns import register_campaign_tools
from app.mcp_server.tools.contacts import register_contact_tools
from app.mcp_server.tools.lists import register_list_tools
from app.mcp_server.tools.mailboxes import register_mailbox_tools
from app.mcp_server.tools.sending import register_sending_tools
from app.mcp_server.tools.deliverability import register_deliverability_tools
from app.mcp_server.tools.warmup import register_warmup_tools
from app.mcp_server.tools.health import register_health_tools

logger = logging.getLogger(__name__)


def create_server() -> Server:
    """Create and configure the MCP server with all CRM tools."""
    server = Server("cold-email-crm")

    # Collect all tool definitions
    all_tools: dict[str, dict] = {}

    register_campaign_tools(all_tools)
    register_contact_tools(all_tools)
    register_list_tools(all_tools)
    register_mailbox_tools(all_tools)
    register_sending_tools(all_tools)
    register_deliverability_tools(all_tools)
    register_warmup_tools(all_tools)
    register_health_tools(all_tools)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = []
        for name, info in all_tools.items():
            tools.append(Tool(
                name=name,
                description=info["description"],
                inputSchema=info["schema"],
            ))
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name not in all_tools:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        handler = all_tools[name]["handler"]
        try:
            result = handler(arguments)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.exception("MCP tool %s failed", name)
            return [TextContent(type="text", text=f"Error: {e}")]

    return server
