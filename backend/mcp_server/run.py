"""Entrypoint to run the MCP Server with SSE transport."""

from __future__ import annotations

import logging
import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp_server.server import create_mcp_server
from mcp_server.tool_registry import ToolRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
BUILTIN_CONFIG_DIR = os.environ.get(
    "API_CONFIG_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api_configs"),
)
USER_CONFIG_DIR = os.environ.get(
    "USER_CONFIG_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_api_configs"),
)
MCP_PORT = int(os.environ.get("MCP_PORT", "8001"))

# Create the tool registry and MCP server
registry = ToolRegistry(builtin_config_dir=BUILTIN_CONFIG_DIR, user_config_dir=USER_CONFIG_DIR)
mcp_server = create_mcp_server(registry)

# SSE transport
sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    """Handle SSE connection from MCP clients."""
    async with sse_transport.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())


async def handle_reload(request: Request):
    """Reload the tool registry from disk."""
    registry.reload()
    return JSONResponse({"status": "reloaded", "tools": len(registry.get_tool_names())})


async def handle_health(request: Request):
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "tools": len(registry.get_tool_names()),
            "tool_names": registry.get_tool_names(),
        }
    )


# Build the Starlette app
app = Starlette(
    routes=[
        Route("/health", handle_health, methods=["GET"]),
        Route("/reload", handle_reload, methods=["POST"]),
        Route("/sse", handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
)


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting MCP Server on port {MCP_PORT}")
    logger.info(f"Built-in configs: {BUILTIN_CONFIG_DIR}")
    logger.info(f"User configs: {USER_CONFIG_DIR}")
    logger.info(f"Tools loaded: {registry.get_tool_names()}")
    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT)
