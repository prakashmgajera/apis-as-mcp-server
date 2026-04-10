"""Frontend simulator integration tests.

These tests simulate the exact HTTP call sequence that the Next.js frontend
makes to the FastAPI backend, including:
  1. CopilotKit agent discovery (/copilotkit/info)
  2. Tool listing for the ToolSelector sidebar (GET /api/tools)
  3. Config management for the ApiConfigManager (GET/POST/PUT/DELETE /api/configs)
  4. Chat with selected tools header (POST /copilotkit with X-Selected-Tools)

The tests do NOT require a running MCP server — they mock the MCP connection
where needed and test the backend's handling of frontend-shaped requests.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ── Simulate: Frontend loads ConfigPanel → user picks model → enters chat ──


class TestFrontendBootSequence:
    """Simulate the frontend boot: ConfigPanel → ChatAgent mount → /info call."""

    @pytest.mark.asyncio
    async def test_step1_copilotkit_info_discovery(self, api_client: AsyncClient):
        """
        When ChatAgent mounts, CopilotKit calls POST /copilotkit/info
        with NO auth headers (no API key yet). The backend must return
        the agent list so the frontend can resolve 'api_agent'.
        """
        resp = await api_client.post(
            "/copilotkit/info",
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert "agents" in data
        agents = data["agents"]
        assert len(agents) >= 1

        api_agent = next((a for a in agents if a["name"] == "api_agent"), None)
        assert api_agent is not None, "Frontend expects to find 'api_agent'"
        assert api_agent["description"] != ""

    @pytest.mark.asyncio
    async def test_step1_copilotkit_info_response_structure(self, api_client: AsyncClient):
        """CopilotKit /info response must have agents, actions, and sdkVersion."""
        resp = await api_client.post("/copilotkit/info", json={})
        data = resp.json()

        assert "agents" in data
        assert "actions" in data
        assert "sdkVersion" in data
        assert isinstance(data["agents"], list)
        assert isinstance(data["actions"], list)


# ── Simulate: ToolSelector sidebar fetches tools ────────────────────────


class TestFrontendToolSelector:
    """Simulate the ToolSelector component fetching and displaying tools."""

    @pytest.mark.asyncio
    async def test_tool_list_with_mcp_unavailable(self, api_client: AsyncClient):
        """
        When ToolSelector calls GET /api/tools and the MCP server is unreachable,
        the backend returns an error response (not a crash).
        """
        resp = await api_client.get("/api/tools")
        assert resp.status_code == 200

        data = resp.json()
        # Either tools or error — should not crash
        assert "tools" in data

    @pytest.mark.asyncio
    async def test_tool_list_with_mocked_mcp(self, api_client: AsyncClient):
        """
        Simulate what happens when the MCP server IS available:
        mock the MCP client to return tools, and verify the response shape
        matches what the frontend ToolSelector expects.
        """
        mock_tool_1 = type("MockTool", (), {"name": "list_posts", "description": "List all posts"})()
        mock_tool_2 = type("MockTool", (), {"name": "get_user", "description": "Get user by ID"})()

        mock_client = AsyncMock()
        mock_client.get_tools = AsyncMock(return_value=[mock_tool_1, mock_tool_2])

        # MultiServerMCPClient is imported inside the route function body,
        # so we must patch it at its origin module.
        with patch(
            "langchain_mcp_adapters.client.MultiServerMCPClient",
            return_value=mock_client,
        ):
            # Also mock the httpx health check to succeed
            mock_http_resp = AsyncMock()
            mock_http_resp.status_code = 200
            mock_http_resp.json.return_value = {
                "status": "healthy",
                "tools": 2,
                "tool_names": ["list_posts", "get_user"],
            }
            mock_http_resp.raise_for_status = lambda: None

            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(return_value=mock_http_resp)
            mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.__aexit__ = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient", return_value=mock_http_client):
                resp = await api_client.get("/api/tools")

        assert resp.status_code == 200
        data = resp.json()

        assert data["count"] == 2
        assert len(data["tools"]) == 2

        # Verify shape matches what frontend expects: {name, description}
        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool

        tool_names = {t["name"] for t in data["tools"]}
        assert tool_names == {"list_posts", "get_user"}


# ── Simulate: ApiConfigManager views ─────────────────────────────────────


class TestFrontendConfigManager:
    """
    Simulate the ApiConfigManager component:
    - On mount: GET /api/configs to list all
    - User clicks "Add New API": POST /api/configs
    - User clicks "Edit": PUT /api/configs/{id}
    - User clicks "Delete": DELETE /api/configs/{id}
    """

    @pytest.mark.asyncio
    async def test_config_manager_loads_on_mount(self, api_client: AsyncClient):
        """On mount, the component fetches all configs for display."""
        resp = await api_client.get("/api/configs")
        assert resp.status_code == 200

        data = resp.json()
        # Frontend expects: configs array, builtin_count, user_count
        assert isinstance(data["configs"], list)
        assert isinstance(data["builtin_count"], int)
        assert isinstance(data["user_count"], int)

        # Each config must have the fields the ConfigCard component needs
        for config in data["configs"]:
            assert "id" in config
            assert "name" in config
            assert "description" in config
            assert "method" in config
            assert "base_url" in config
            assert "path" in config
            assert "source" in config  # "builtin" or "user"
            assert config["source"] in ("builtin", "user")

    @pytest.mark.asyncio
    async def test_config_builder_creates_api(
        self, api_client: AsyncClient, sample_user_config_data: dict
    ):
        """
        Simulate the ApiConfigBuilder form submission.
        The frontend sends the exact shape produced by the form.
        """
        resp = await api_client.post("/api/configs", json=sample_user_config_data)
        assert resp.status_code == 201

        data = resp.json()
        # Frontend expects the created config back with id and timestamps
        assert "id" in data
        assert "created_at" in data
        assert data["name"] == sample_user_config_data["name"]

    @pytest.mark.asyncio
    async def test_config_builder_edit_flow(
        self, api_client: AsyncClient, sample_user_config_data: dict
    ):
        """
        Simulate: user creates a config, then clicks Edit and changes description.
        The ApiConfigBuilder pre-fills the form and sends PUT on save.
        """
        # Create
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        config_id = create_resp.json()["id"]

        # Edit: user changes description and timeout
        edited = {
            **sample_user_config_data,
            "description": "Updated weather API with new endpoint",
            "timeout": 45,
        }
        put_resp = await api_client.put(f"/api/configs/{config_id}", json=edited)
        assert put_resp.status_code == 200
        assert put_resp.json()["description"] == "Updated weather API with new endpoint"
        assert put_resp.json()["timeout"] == 45

    @pytest.mark.asyncio
    async def test_config_manager_delete_with_confirm(
        self, api_client: AsyncClient, sample_user_config_data: dict
    ):
        """
        Simulate: user clicks Delete, confirms, and the config is removed.
        Frontend calls DELETE /api/configs/{id}.
        """
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        config_id = create_resp.json()["id"]

        del_resp = await api_client.delete(f"/api/configs/{config_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        # Verify it's gone from the list
        list_resp = await api_client.get("/api/configs")
        assert list_resp.json()["user_count"] == 0


# ── Simulate: Chat with X-Selected-Tools header ──────────────────────────


class TestFrontendChatHeaders:
    """
    Simulate the headers that ChatAgent sends to the backend.
    The frontend CopilotKit component passes these headers on every request.
    """

    @pytest.mark.asyncio
    async def test_selected_tools_header_parsing(self, api_client: AsyncClient):
        """
        When the frontend sends X-Selected-Tools, the middleware should parse it.
        We test this indirectly via /copilotkit/info (no API key = uses placeholder).
        The middleware runs but falls through to the placeholder.
        """
        resp = await api_client.post(
            "/copilotkit/info",
            json={},
            headers={
                "X-Model-Provider": "openai",
                "X-Model-Name": "gpt-4o",
                "X-Selected-Tools": "list_posts,get_user,create_post",
                # No X-Api-Key → middleware falls through to placeholder
            },
        )
        # Should still work (placeholder handles /info)
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data

    @pytest.mark.asyncio
    async def test_empty_selected_tools_header(self, api_client: AsyncClient):
        """Empty X-Selected-Tools is handled gracefully (uses all tools)."""
        resp = await api_client.post(
            "/copilotkit/info",
            json={},
            headers={
                "X-Selected-Tools": "",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_selected_tools_header(self, api_client: AsyncClient):
        """Missing X-Selected-Tools header is handled gracefully."""
        resp = await api_client.post(
            "/copilotkit/info",
            json={},
        )
        assert resp.status_code == 200


# ── Simulate: Full user session ──────────────────────────────────────────


class TestFullUserSession:
    """
    Simulate a complete user session from the frontend's perspective:
    1. Open app → ConfigPanel renders
    2. User selects model + enters API key → ChatAgent mounts
    3. ChatAgent triggers /copilotkit/info → discovers api_agent
    4. ToolSelector sidebar opens → GET /api/tools
    5. User navigates to Manage APIs → GET /api/configs
    6. User creates a new API config → POST /api/configs
    7. User returns to chat → sends message with selected tools
    """

    @pytest.mark.asyncio
    async def test_complete_session_flow(
        self, api_client: AsyncClient, sample_user_config_data: dict
    ):
        # Step 3: Agent discovery
        info_resp = await api_client.post("/copilotkit/info", json={})
        assert info_resp.status_code == 200
        assert any(
            a["name"] == "api_agent" for a in info_resp.json()["agents"]
        ), "api_agent must be discoverable"

        # Step 5: View configs
        configs_resp = await api_client.get("/api/configs")
        assert configs_resp.status_code == 200
        initial_builtin = configs_resp.json()["builtin_count"]
        assert initial_builtin > 0, "Should have built-in configs"

        # Step 6: Create new API config
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        assert create_resp.status_code == 201
        new_config_id = create_resp.json()["id"]

        # Verify it appears in listing
        configs_resp2 = await api_client.get("/api/configs")
        assert configs_resp2.json()["user_count"] == 1

        # Step 7: Chat request with selected tools
        # (We can't actually complete a chat without an LLM key, but we can
        # verify the middleware handles the headers correctly by checking
        # that /info still works with all the headers the frontend sends)
        chat_headers = {
            "X-Model-Provider": "openai",
            "X-Model-Name": "gpt-4o",
            "X-Selected-Tools": "test_list_posts,test_weather_api",
            # No real API key - just testing header parsing
        }
        info_resp2 = await api_client.post(
            "/copilotkit/info",
            json={},
            headers=chat_headers,
        )
        assert info_resp2.status_code == 200

        # Cleanup: delete the user config
        del_resp = await api_client.delete(f"/api/configs/{new_config_id}")
        assert del_resp.status_code == 200


# ── Simulate: ConfigPanel model validation ───────────────────────────────


class TestFrontendValidation:
    """
    Test that the backend validates input the same way the frontend does.
    These simulate what happens if the frontend validation is bypassed.
    """

    @pytest.mark.asyncio
    async def test_rejects_config_with_special_chars_in_name(self, api_client: AsyncClient):
        """Tool names must be valid Python identifiers (alphanumeric + underscore)."""
        payload = {
            "name": "my-api-tool",  # dashes not allowed
            "description": "test",
            "base_url": "https://example.com",
            "path": "/test",
        }
        resp = await api_client.post("/api/configs", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_config_with_spaces_in_name(self, api_client: AsyncClient):
        payload = {
            "name": "my tool",
            "description": "test",
            "base_url": "https://example.com",
            "path": "/test",
        }
        resp = await api_client.post("/api/configs", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_config_starting_with_number(self, api_client: AsyncClient):
        payload = {
            "name": "123tool",
            "description": "test",
            "base_url": "https://example.com",
            "path": "/test",
        }
        resp = await api_client.post("/api/configs", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_accepts_underscore_prefixed_name(self, api_client: AsyncClient):
        payload = {
            "name": "_private_api",
            "description": "test",
            "base_url": "https://example.com",
            "path": "/test",
        }
        resp = await api_client.post("/api/configs", json=payload)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_rejects_invalid_http_method(self, api_client: AsyncClient):
        payload = {
            "name": "test_api",
            "description": "test",
            "base_url": "https://example.com",
            "path": "/test",
            "method": "INVALID",
        }
        resp = await api_client.post("/api/configs", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_timeout_too_high(self, api_client: AsyncClient):
        payload = {
            "name": "test_api",
            "description": "test",
            "base_url": "https://example.com",
            "path": "/test",
            "timeout": 999,
        }
        resp = await api_client.post("/api/configs", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_timeout_zero(self, api_client: AsyncClient):
        payload = {
            "name": "test_api",
            "description": "test",
            "base_url": "https://example.com",
            "path": "/test",
            "timeout": 0,
        }
        resp = await api_client.post("/api/configs", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_accepts_all_http_methods(self, api_client: AsyncClient):
        """All valid HTTP methods should be accepted."""
        for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            payload = {
                "name": f"test_{method.lower()}",
                "description": f"test {method}",
                "base_url": "https://example.com",
                "path": "/test",
                "method": method,
            }
            resp = await api_client.post("/api/configs", json=payload)
            assert resp.status_code == 201, f"Method {method} should be accepted"

    @pytest.mark.asyncio
    async def test_accepts_all_auth_types(self, api_client: AsyncClient):
        """All valid auth types should be accepted."""
        for auth_type in ["none", "bearer", "api_key", "basic"]:
            payload = {
                "name": f"test_auth_{auth_type}",
                "description": "test",
                "base_url": "https://example.com",
                "path": "/test",
                "auth": {"type": auth_type},
            }
            resp = await api_client.post("/api/configs", json=payload)
            assert resp.status_code == 201, f"Auth type {auth_type} should be accepted"

    @pytest.mark.asyncio
    async def test_accepts_all_parameter_locations(self, api_client: AsyncClient):
        """All valid parameter locations should be accepted."""
        for location in ["query", "path", "header", "body"]:
            payload = {
                "name": f"test_param_{location}",
                "description": "test",
                "base_url": "https://example.com",
                "path": "/test",
                "parameters": [
                    {"name": "param1", "type": "string", "location": location}
                ],
            }
            resp = await api_client.post("/api/configs", json=payload)
            assert resp.status_code == 201, f"Location {location} should be accepted"
