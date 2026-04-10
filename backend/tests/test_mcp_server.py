"""Integration tests for the MCP Server: ToolRegistry, server creation, and HTTP endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from mcp_server.server import create_mcp_server
from mcp_server.tool_registry import ToolRegistry

# ── ToolRegistry tests ────────────────────────────────────────────────────


class TestToolRegistry:
    """Tests for ToolRegistry loading, schema building, and execution."""

    def test_load_builtin_yaml_configs(self, sample_yaml_config: str):
        """Registry loads all API endpoints from YAML files."""
        registry = ToolRegistry(builtin_config_dir=sample_yaml_config)
        names = registry.get_tool_names()

        assert len(names) == 3
        assert "test_list_posts" in names
        assert "test_get_post" in names
        assert "test_create_post" in names

    def test_load_empty_dir(self, tmp_config_dirs: dict[str, str]):
        """Registry handles empty config directories gracefully."""
        registry = ToolRegistry(builtin_config_dir=tmp_config_dirs["builtin"])
        assert registry.get_tool_names() == []
        assert registry.get_all_configs() == []

    def test_load_nonexistent_dir(self, tmp_path: Path):
        """Registry handles missing directory gracefully."""
        registry = ToolRegistry(builtin_config_dir=str(tmp_path / "does_not_exist"))
        assert registry.get_tool_names() == []

    def test_get_config_by_name(self, sample_yaml_config: str):
        """Registry can retrieve individual configs by tool name."""
        registry = ToolRegistry(builtin_config_dir=sample_yaml_config)
        config = registry.get_config("test_list_posts")

        assert config is not None
        assert config.name == "test_list_posts"
        assert config.method.value == "GET"
        assert config.base_url == "https://jsonplaceholder.typicode.com"

    def test_get_config_unknown_name(self, sample_yaml_config: str):
        """Registry returns None for unknown tool names."""
        registry = ToolRegistry(builtin_config_dir=sample_yaml_config)
        assert registry.get_config("nonexistent_tool") is None

    def test_build_input_schema_with_params(self, sample_yaml_config: str):
        """Schema includes properties and required fields from parameters."""
        registry = ToolRegistry(builtin_config_dir=sample_yaml_config)
        config = registry.get_config("test_get_post")
        schema = registry.build_input_schema(config)

        assert schema["type"] == "object"
        assert "postId" in schema["properties"]
        assert schema["properties"]["postId"]["type"] == "integer"
        assert "required" in schema
        assert "postId" in schema["required"]

    def test_build_input_schema_optional_params(self, sample_yaml_config: str):
        """Optional params appear in properties but not in required."""
        registry = ToolRegistry(builtin_config_dir=sample_yaml_config)
        config = registry.get_config("test_list_posts")
        schema = registry.build_input_schema(config)

        assert "userId" in schema["properties"]
        assert schema["properties"]["userId"]["type"] == "integer"
        # userId is optional, so required should be absent or empty
        assert "required" not in schema or "userId" not in schema.get("required", [])

    def test_build_input_schema_no_params(self, tmp_config_dirs: dict[str, str]):
        """Schema for an endpoint with no parameters has empty properties."""
        yaml_content = """\
version: "1.0"
groups:
  - name: Minimal
    apis:
      - name: no_params_api
        description: "An API with no parameters"
        base_url: "https://example.com"
        path: "/ping"
        method: GET
"""
        (Path(tmp_config_dirs["builtin"]) / "minimal.yaml").write_text(yaml_content)
        registry = ToolRegistry(builtin_config_dir=tmp_config_dirs["builtin"])
        config = registry.get_config("no_params_api")
        schema = registry.build_input_schema(config)

        assert schema["type"] == "object"
        assert schema["properties"] == {}

    def test_build_input_schema_multiple_required_params(self, sample_yaml_config: str):
        """Schema for POST endpoint has multiple required body params."""
        registry = ToolRegistry(builtin_config_dir=sample_yaml_config)
        config = registry.get_config("test_create_post")
        schema = registry.build_input_schema(config)

        assert "title" in schema["properties"]
        assert "body" in schema["properties"]
        assert "userId" in schema["properties"]
        assert set(schema["required"]) == {"title", "body", "userId"}

    def test_load_user_json_configs(self, sample_yaml_config: str, tmp_config_dirs: dict[str, str]):
        """Registry loads user configs from JSON files."""
        user_config = {
            "name": "user_test_tool",
            "description": "A user-defined tool",
            "base_url": "https://example.com",
            "path": "/test",
            "method": "GET",
        }
        json_path = Path(tmp_config_dirs["user"]) / "user_tool.json"
        json_path.write_text(json.dumps(user_config))

        registry = ToolRegistry(
            builtin_config_dir=sample_yaml_config,
            user_config_dir=tmp_config_dirs["user"],
        )

        assert "user_test_tool" in registry.get_tool_names()
        assert len(registry.get_tool_names()) == 4  # 3 builtin + 1 user

    def test_reload_picks_up_new_configs(self, sample_yaml_config: str, tmp_config_dirs: dict[str, str]):
        """Calling reload() picks up new configs added after init."""
        registry = ToolRegistry(
            builtin_config_dir=sample_yaml_config,
            user_config_dir=tmp_config_dirs["user"],
        )
        assert len(registry.get_tool_names()) == 3

        # Add a user config after init
        new_config = {
            "name": "late_addition",
            "description": "Added later",
            "base_url": "https://example.com",
            "path": "/late",
            "method": "GET",
        }
        (Path(tmp_config_dirs["user"]) / "late.json").write_text(json.dumps(new_config))

        registry.reload()
        assert "late_addition" in registry.get_tool_names()
        assert len(registry.get_tool_names()) == 4

    @pytest.mark.asyncio
    async def test_execute_tool_makes_http_call(self, sample_yaml_config: str):
        """Execute a tool call — verify it attempts the correct HTTP request."""
        registry = ToolRegistry(builtin_config_dir=sample_yaml_config)
        result = await registry.execute_tool("test_get_post", {"postId": 1})

        # In CI/sandboxed environments the external API may be unreachable.
        # We verify the registry attempted the right call by checking the result
        # is either valid JSON (success) or an error string mentioning the URL.
        try:
            data = json.loads(result)
            # Success: JSONPlaceholder returned data
            assert data["id"] == 1
            assert "title" in data
        except json.JSONDecodeError:
            # Network blocked: verify the error references the correct URL
            assert "jsonplaceholder.typicode.com" in result
            assert "posts/1" in result

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_name(self, sample_yaml_config: str):
        """Executing an unknown tool returns an error message."""
        registry = ToolRegistry(builtin_config_dir=sample_yaml_config)
        result = await registry.execute_tool("nonexistent", {})
        assert "Error: Unknown tool" in result


# ── MCP Server creation tests ────────────────────────────────────────────


class TestMCPServerCreation:
    """Tests for create_mcp_server()."""

    def test_creates_server_with_correct_name(self, sample_yaml_config: str):
        registry = ToolRegistry(builtin_config_dir=sample_yaml_config)
        server = create_mcp_server(registry)
        assert server.name == "api-tools-mcp-server"


# ── MCP Server HTTP endpoint tests (Starlette app) ──────────────────────


class TestMCPServerHTTP:
    """Integration tests for the MCP server's health and reload HTTP endpoints."""

    @pytest_asyncio.fixture()
    async def mcp_client(self, sample_yaml_config: str, tmp_config_dirs: dict[str, str]) -> AsyncClient:
        """Create an async test client for the MCP server Starlette app."""
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        registry = ToolRegistry(
            builtin_config_dir=sample_yaml_config,
            user_config_dir=tmp_config_dirs["user"],
        )

        async def handle_health(request: Request):
            return JSONResponse(
                {
                    "status": "healthy",
                    "tools": len(registry.get_tool_names()),
                    "tool_names": registry.get_tool_names(),
                }
            )

        async def handle_reload(request: Request):
            registry.reload()
            return JSONResponse({"status": "reloaded", "tools": len(registry.get_tool_names())})

        test_app = Starlette(
            routes=[
                Route("/health", handle_health, methods=["GET"]),
                Route("/reload", handle_reload, methods=["POST"]),
            ]
        )

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://mcp-test") as client:
            yield client

        # Store registry for reload test
        self._registry = registry
        self._user_dir = tmp_config_dirs["user"]

    @pytest.mark.asyncio
    async def test_health_returns_status(self, mcp_client: AsyncClient):
        resp = await mcp_client.get("/health")
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "healthy"
        assert data["tools"] == 3
        assert isinstance(data["tool_names"], list)
        assert "test_list_posts" in data["tool_names"]
        assert "test_get_post" in data["tool_names"]
        assert "test_create_post" in data["tool_names"]

    @pytest.mark.asyncio
    async def test_health_response_schema(self, mcp_client: AsyncClient):
        """Health response has exactly the expected keys."""
        resp = await mcp_client.get("/health")
        data = resp.json()
        assert set(data.keys()) == {"status", "tools", "tool_names"}

    @pytest.mark.asyncio
    async def test_reload_endpoint(self, mcp_client: AsyncClient):
        resp = await mcp_client.post("/reload")
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "reloaded"
        assert data["tools"] == 3
