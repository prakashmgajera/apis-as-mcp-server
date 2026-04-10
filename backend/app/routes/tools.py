"""Routes for listing available MCP tools."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tools"])


@router.get("/tools")
async def list_tools():
    """List all available tools from the MCP server.

    Returns a lightweight summary for each tool suitable for the
    frontend tool selector UI.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Use the MCP server's health endpoint which includes tool names
            resp = await client.get(settings.mcp_server_url.replace("/sse", "/health"))
            resp.raise_for_status()
            health_data = resp.json()
    except Exception as e:
        logger.exception("Failed to fetch tools from MCP server")
        return {"error": str(e), "tools": []}

    # Get detailed tool info by connecting via MCP client
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        mcp_client = MultiServerMCPClient(
            {
                "api-tools": {
                    "transport": "sse",
                    "url": settings.mcp_server_url,
                    "timeout": 10,
                },
            }
        )
        mcp_tools = await mcp_client.get_tools()

        tools = []
        for tool in mcp_tools:
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                }
            )

        return {"tools": tools, "count": len(tools)}

    except Exception:
        logger.exception("Failed to fetch tool details from MCP server")
        # Fall back to just tool names from health endpoint
        tool_names = health_data.get("tool_names", [])
        tools = [{"name": name, "description": ""} for name in tool_names]
        return {"tools": tools, "count": len(tools)}
