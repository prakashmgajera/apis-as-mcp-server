"""Shared test fixtures for integration tests."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure backend package is importable
os.environ.setdefault("API_CONFIG_DIR", os.path.join(os.path.dirname(__file__), "..", "api_configs"))


@pytest.fixture()
def tmp_config_dirs() -> Generator[dict[str, str], None, None]:
    """Create temporary directories for builtin and user configs."""
    builtin_dir = tempfile.mkdtemp(prefix="test_builtin_")
    user_dir = tempfile.mkdtemp(prefix="test_user_")
    yield {"builtin": builtin_dir, "user": user_dir}
    shutil.rmtree(builtin_dir, ignore_errors=True)
    shutil.rmtree(user_dir, ignore_errors=True)


@pytest.fixture()
def sample_yaml_config(tmp_config_dirs: dict[str, str]) -> str:
    """Write a minimal YAML config into the builtin dir and return the dir path."""
    yaml_content = """\
version: "1.0"
groups:
  - name: TestAPIs
    description: Test APIs for integration testing
    apis:
      - name: test_list_posts
        description: "List all test posts"
        base_url: "https://jsonplaceholder.typicode.com"
        path: "/posts"
        method: GET
        parameters:
          - name: userId
            description: "Filter by user ID"
            type: integer
            required: false
            location: query

      - name: test_get_post
        description: "Get a single test post"
        base_url: "https://jsonplaceholder.typicode.com"
        path: "/posts/{postId}"
        method: GET
        parameters:
          - name: postId
            description: "Post ID"
            type: integer
            required: true
            location: path

      - name: test_create_post
        description: "Create a test post"
        base_url: "https://jsonplaceholder.typicode.com"
        path: "/posts"
        method: POST
        headers:
          Content-Type: "application/json"
        parameters:
          - name: title
            description: "Post title"
            type: string
            required: true
            location: body
          - name: body
            description: "Post body"
            type: string
            required: true
            location: body
          - name: userId
            description: "Author user ID"
            type: integer
            required: true
            location: body
"""
    config_path = Path(tmp_config_dirs["builtin"]) / "test_apis.yaml"
    config_path.write_text(yaml_content)
    return tmp_config_dirs["builtin"]


@pytest.fixture()
def sample_user_config_data() -> dict:
    """Return a valid user API config payload (as sent by the frontend)."""
    return {
        "name": "test_weather_api",
        "description": "Get weather for a city",
        "base_url": "https://api.weatherapi.com/v1",
        "path": "/current.json",
        "method": "GET",
        "parameters": [
            {
                "name": "q",
                "description": "City name",
                "type": "string",
                "required": True,
                "location": "query",
            },
            {
                "name": "key",
                "description": "API key",
                "type": "string",
                "required": True,
                "location": "query",
            },
        ],
        "headers": {},
        "auth": {"type": "none", "token_env_var": None, "header_name": "Authorization", "prefix": "Bearer"},
        "timeout": 30,
        "response_template": None,
        "group_name": "Weather",
    }


# ---------------------------------------------------------------------------
# FastAPI test client (uses the real app but with overridden config dirs)
# ---------------------------------------------------------------------------


@pytest.fixture()
def patched_settings(tmp_config_dirs: dict[str, str], sample_yaml_config: str):
    """Temporarily patch app settings to use temp config dirs."""
    from app.config import settings

    original_api = settings.api_config_dir
    original_user = settings.user_config_dir
    original_mcp = settings.mcp_server_url

    settings.api_config_dir = sample_yaml_config
    settings.user_config_dir = tmp_config_dirs["user"]
    # Point MCP URL to a non-existent server (routes that need it will handle errors gracefully)
    settings.mcp_server_url = "http://localhost:19999/sse"

    yield settings

    settings.api_config_dir = original_api
    settings.user_config_dir = original_user
    settings.mcp_server_url = original_mcp


@pytest_asyncio.fixture()
async def api_client(patched_settings) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client hitting the FastAPI app directly (no network)."""
    # Re-initialize the storage in the configs router to use the patched dir
    # Replace the module-level storage with one pointing at the temp dir
    import app.routes.api_configs as configs_mod
    from app.storage import ConfigStorage

    original_storage = configs_mod.storage
    configs_mod.storage = ConfigStorage(patched_settings.user_config_dir)

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    configs_mod.storage = original_storage
