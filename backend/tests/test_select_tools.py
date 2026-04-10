"""Tests for the select tool feature.

Covers the full flow: tool listing endpoint, middleware header parsing,
and agent-level tool filtering based on user selection.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

# ── Helper: create mock MCP tools ────────────────────────────────────────


def _make_mock_tool(name: str, description: str = "") -> MagicMock:
    tool = MagicMock()
    tool.name = name
    tool.description = description or f"Description for {name}"
    return tool


MOCK_TOOLS = [
    _make_mock_tool("list_posts", "List all posts"),
    _make_mock_tool("get_post", "Get a single post"),
    _make_mock_tool("create_post", "Create a new post"),
    _make_mock_tool("delete_post", "Delete a post"),
    _make_mock_tool("get_user", "Get user details"),
]


def _patch_mcp_client(target="langchain_mcp_adapters.client.MultiServerMCPClient", tools=None):
    """Return a context manager that patches MultiServerMCPClient to return the given tools."""
    if tools is None:
        tools = list(MOCK_TOOLS)
    mock_client = AsyncMock()
    mock_client.get_tools = AsyncMock(return_value=tools)
    return patch(target, return_value=mock_client)


def _patch_health_check(success=True, tool_names=None):
    """Return a context manager that patches the httpx health check."""
    if success:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "healthy",
            "tools": len(tool_names or []),
            "tool_names": tool_names or [],
        }
        mock_resp.raise_for_status = MagicMock()
    else:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock(side_effect=Exception("Connection refused"))

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    return patch("httpx.AsyncClient", return_value=mock_http_client)


# ── /api/tools endpoint tests ────────────────────────────────────────────


class TestToolsEndpoint:
    """Tests for GET /api/tools — the endpoint that powers the ToolSelector UI."""

    @pytest.mark.asyncio
    async def test_returns_all_tools_with_name_and_description(self, api_client: AsyncClient):
        """Endpoint returns tools with correct shape for the frontend ToolSelector."""
        with _patch_health_check(success=True, tool_names=["list_posts", "get_post"]), _patch_mcp_client():
            resp = await api_client.get("/api/tools")

        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert "count" in data
        assert data["count"] == 5
        assert len(data["tools"]) == 5

        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool

    @pytest.mark.asyncio
    async def test_returns_tools_when_health_check_fails(self, api_client: AsyncClient):
        """Tools must be returned even when the MCP health endpoint is unreachable.

        The /api/tools route should not gate on a health check. The MCP client
        connection is what matters — if it can fetch tools, the health check
        status is irrelevant.
        """
        with _patch_health_check(success=False), _patch_mcp_client():
            resp = await api_client.get("/api/tools")

        assert resp.status_code == 200
        data = resp.json()
        # Must still return tools from MCP client even though health check failed
        assert data["count"] == 5
        assert len(data["tools"]) == 5
        tool_names = {t["name"] for t in data["tools"]}
        assert "list_posts" in tool_names
        assert "get_user" in tool_names

    @pytest.mark.asyncio
    async def test_error_response_includes_count_field(self, api_client: AsyncClient):
        """Error responses must include the count field for frontend compatibility.

        The frontend ToolsResponse type expects { tools, count }. A response
        without count will cause TypeScript type errors or undefined behavior.
        """
        # Both health check and MCP client fail
        resp = await api_client.get("/api/tools")

        data = resp.json()
        assert "tools" in data
        assert "count" in data  # Must always be present
        assert isinstance(data["count"], int)


# ── Middleware header parsing tests ───────────────────────────────────────


class TestMiddlewareSelectedToolsParsing:
    """Tests that the middleware correctly parses X-Selected-Tools header."""

    @pytest.mark.asyncio
    async def test_selected_tools_header_parsed_correctly(self, api_client: AsyncClient):
        """Comma-separated tool names should be parsed into a list."""
        with patch("app.main.create_agent") as mock_create:
            mock_create.return_value = _create_noop_graph()
            await api_client.post(
                "/copilotkit/info",
                json={},
                headers={
                    "X-Model-Provider": "openai",
                    "X-Model-Name": "gpt-4o",
                    "X-Api-Key": "sk-test-key-123",
                    "X-Selected-Tools": "list_posts,get_user,create_post",
                },
            )

        mock_create.assert_called_once()
        selected = mock_create.call_args.kwargs["selected_tools"]
        assert selected == ["list_posts", "get_user", "create_post"]

    @pytest.mark.asyncio
    async def test_selected_tools_with_whitespace_trimmed(self, api_client: AsyncClient):
        """Whitespace around tool names should be stripped."""
        with patch("app.main.create_agent") as mock_create:
            mock_create.return_value = _create_noop_graph()
            await api_client.post(
                "/copilotkit/info",
                json={},
                headers={
                    "X-Model-Provider": "openai",
                    "X-Model-Name": "gpt-4o",
                    "X-Api-Key": "sk-test-key-123",
                    "X-Selected-Tools": " list_posts , get_user , create_post ",
                },
            )

        selected = mock_create.call_args.kwargs["selected_tools"]
        assert selected == ["list_posts", "get_user", "create_post"]

    @pytest.mark.asyncio
    async def test_empty_header_means_all_tools(self, api_client: AsyncClient):
        """Empty X-Selected-Tools header should result in selected_tools=None (use all)."""
        with patch("app.main.create_agent") as mock_create:
            mock_create.return_value = _create_noop_graph()
            await api_client.post(
                "/copilotkit/info",
                json={},
                headers={
                    "X-Model-Provider": "openai",
                    "X-Model-Name": "gpt-4o",
                    "X-Api-Key": "sk-test-key-123",
                    "X-Selected-Tools": "",
                },
            )

        selected = mock_create.call_args.kwargs["selected_tools"]
        assert selected is None

    @pytest.mark.asyncio
    async def test_missing_header_means_all_tools(self, api_client: AsyncClient):
        """Missing X-Selected-Tools header should result in selected_tools=None (use all)."""
        with patch("app.main.create_agent") as mock_create:
            mock_create.return_value = _create_noop_graph()
            await api_client.post(
                "/copilotkit/info",
                json={},
                headers={
                    "X-Model-Provider": "openai",
                    "X-Model-Name": "gpt-4o",
                    "X-Api-Key": "sk-test-key-123",
                },
            )

        selected = mock_create.call_args.kwargs["selected_tools"]
        assert selected is None

    @pytest.mark.asyncio
    async def test_single_tool_selected(self, api_client: AsyncClient):
        """Selecting a single tool should result in a list with one element."""
        with patch("app.main.create_agent") as mock_create:
            mock_create.return_value = _create_noop_graph()
            await api_client.post(
                "/copilotkit/info",
                json={},
                headers={
                    "X-Model-Provider": "openai",
                    "X-Model-Name": "gpt-4o",
                    "X-Api-Key": "sk-test-key-123",
                    "X-Selected-Tools": "list_posts",
                },
            )

        selected = mock_create.call_args.kwargs["selected_tools"]
        assert selected == ["list_posts"]


# ── Agent tool filtering tests ────────────────────────────────────────────


async def _run_agent_with_selection(selected_tools):
    """Create an agent with given tool selection, invoke it, and return the tools passed to create_react_agent."""
    from langchain_core.messages import HumanMessage

    from app.agent import create_agent

    with (
        _patch_mcp_client(target="app.agent.MultiServerMCPClient"),
        patch("app.agent._create_model", return_value=AsyncMock()),
    ):
        agent = create_agent(
            provider="openai",
            model_name="gpt-4o",
            api_key="test-key",
            selected_tools=selected_tools,
        )

        mock_inner = AsyncMock()
        mock_inner.ainvoke = AsyncMock(return_value={"messages": []})
        with patch("app.agent.create_react_agent", return_value=mock_inner) as mock_react:
            await agent.ainvoke({"messages": [HumanMessage(content="hello")]})
            return mock_react.call_args.kwargs["tools"]


class TestAgentToolFiltering:
    """Tests that create_agent correctly filters MCP tools based on selection."""

    @pytest.mark.asyncio
    async def test_filters_to_selected_tools(self):
        """When selected_tools is provided, only those tools should be available to the agent."""
        tools_passed = await _run_agent_with_selection(["list_posts", "get_user"])
        tool_names = {t.name for t in tools_passed}
        assert tool_names == {"list_posts", "get_user"}

    @pytest.mark.asyncio
    async def test_none_selected_uses_all_tools(self):
        """When selected_tools is None, all MCP tools should be available."""
        tools_passed = await _run_agent_with_selection(None)
        assert len(tools_passed) == 5

    @pytest.mark.asyncio
    async def test_empty_list_selected_gives_no_tools(self):
        """When selected_tools is an empty list, no tools should be available."""
        tools_passed = await _run_agent_with_selection([])
        assert len(tools_passed) == 0

    @pytest.mark.asyncio
    async def test_nonexistent_tool_selection_gives_empty(self):
        """Selecting a tool that doesn't exist in MCP should result in no tools."""
        tools_passed = await _run_agent_with_selection(["nonexistent_tool"])
        assert len(tools_passed) == 0

    @pytest.mark.asyncio
    async def test_partial_selection_filters_correctly(self):
        """Selecting some valid and some invalid tool names returns only the valid ones."""
        tools_passed = await _run_agent_with_selection(["list_posts", "nonexistent", "get_user"])
        tool_names = {t.name for t in tools_passed}
        assert tool_names == {"list_posts", "get_user"}


# ── Helper ────────────────────────────────────────────────────────────────


def _create_noop_graph():
    """Create a minimal compiled graph for mocking create_agent return value."""
    from langgraph.graph import MessagesState, StateGraph

    graph = StateGraph(MessagesState)
    graph.add_node("noop", lambda state: state)
    graph.set_entry_point("noop")
    graph.set_finish_point("noop")
    return graph.compile()
