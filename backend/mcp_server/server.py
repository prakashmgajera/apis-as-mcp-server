"""MCP Server that dynamically registers REST API endpoints as tools."""

from __future__ import annotations

import logging

from mcp.server import Server
from mcp.types import TextContent, Tool

from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def create_mcp_server(registry: ToolRegistry) -> Server:
    """Create and configure an MCP Server backed by the given ToolRegistry."""

    server = Server("api-tools-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """Return all registered API tools."""
        tools: list[Tool] = []
        for config in registry.get_all_configs():
            input_schema = registry.build_input_schema(config)
            tool = Tool(
                name=config.name,
                description=config.description,
                inputSchema=input_schema,
            )
            tools.append(tool)
        logger.debug(f"list_tools returning {len(tools)} tools")
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Execute the API call for the requested tool."""
        logger.info(f"call_tool: {name} with args {arguments}")
        result = await registry.execute_tool(name, arguments)
        return [TextContent(type="text", text=result)]

    return server
