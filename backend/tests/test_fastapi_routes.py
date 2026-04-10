"""Integration tests for FastAPI routes: health, configs CRUD, and CopilotKit discovery."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# ── Health endpoint ───────────────────────────────────────────────────────


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, api_client: AsyncClient):
        resp = await api_client.get("/health")
        assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "healthy"
        assert "app" in data

    @pytest.mark.asyncio
    async def test_health_response_schema(self, api_client: AsyncClient):
        resp = await api_client.get("/health")
        data = resp.json()
        assert set(data.keys()) == {"status", "app"}


# ── CopilotKit agent discovery ───────────────────────────────────────────


class TestCopilotKitDiscovery:
    @pytest.mark.asyncio
    async def test_copilotkit_info_returns_agent(self, api_client: AsyncClient):
        """The /copilotkit/info endpoint must return api_agent so the frontend can find it."""
        resp = await api_client.post(
            "/copilotkit/info",
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert "agents" in data
        assert "api_agent" in data["agents"]

    @pytest.mark.asyncio
    async def test_copilotkit_info_agents_is_dict_keyed_by_name(self, api_client: AsyncClient):
        """Frontend v1.x expects agents as a dict keyed by agent name, NOT an array.

        Object.entries(array) yields ["0", ...] keys, causing "Known agents: [0]"
        instead of finding "api_agent". This test catches the exact failure mode.
        """
        resp = await api_client.post("/copilotkit/info", json={})
        data = resp.json()

        agents = data["agents"]
        # Must be a dict, not a list
        assert isinstance(agents, dict), f"agents must be a dict keyed by name, got {type(agents).__name__}: {agents}"
        # Key must be the agent name
        assert "api_agent" in agents, f"Expected key 'api_agent' in agents dict, got keys: {list(agents.keys())}"
        # Numeric keys like "0" indicate the bug where an array was returned
        for key in agents:
            assert not key.isdigit(), (
                f"Agent key '{key}' is numeric — agents dict was likely an array. "
                "Frontend Object.entries(array) produces numeric keys."
            )

    @pytest.mark.asyncio
    async def test_copilotkit_info_agent_has_description(self, api_client: AsyncClient):
        """Frontend destructures {description} from agent value — it must be present."""
        resp = await api_client.post("/copilotkit/info", json={})
        data = resp.json()
        agent = data["agents"]["api_agent"]
        assert "description" in agent
        assert len(agent["description"]) > 0

    @pytest.mark.asyncio
    async def test_copilotkit_info_has_sdk_version(self, api_client: AsyncClient):
        resp = await api_client.post("/copilotkit/info", json={})
        data = resp.json()
        assert "sdkVersion" in data

    @pytest.mark.asyncio
    async def test_copilotkit_info_via_root_post(self, api_client: AsyncClient):
        """Frontend auto-detect sends POST to root with {method: "info"} body."""
        resp = await api_client.post(
            "/copilotkit/",
            json={"method": "info"},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["agents"], dict)
        assert "api_agent" in data["agents"]


# ── Configs CRUD ─────────────────────────────────────────────────────────


class TestConfigsList:
    @pytest.mark.asyncio
    async def test_list_configs_returns_builtin(self, api_client: AsyncClient):
        """GET /api/configs returns built-in YAML configs."""
        resp = await api_client.get("/api/configs")
        assert resp.status_code == 200

        data = resp.json()
        assert "configs" in data
        assert data["builtin_count"] == 3
        assert data["user_count"] == 0

        names = [c["name"] for c in data["configs"]]
        assert "test_list_posts" in names
        assert "test_get_post" in names
        assert "test_create_post" in names

    @pytest.mark.asyncio
    async def test_list_configs_builtin_have_source(self, api_client: AsyncClient):
        """Built-in configs are tagged with source='builtin'."""
        resp = await api_client.get("/api/configs")
        data = resp.json()

        for config in data["configs"]:
            assert config["source"] == "builtin"

    @pytest.mark.asyncio
    async def test_list_configs_builtin_have_group_name(self, api_client: AsyncClient):
        """Built-in configs include a group_name from the YAML."""
        resp = await api_client.get("/api/configs")
        data = resp.json()

        for config in data["configs"]:
            assert "group_name" in config
            assert config["group_name"] == "TestAPIs"

    @pytest.mark.asyncio
    async def test_list_configs_builtin_ids_prefixed(self, api_client: AsyncClient):
        """Built-in config IDs are prefixed with 'builtin_'."""
        resp = await api_client.get("/api/configs")
        data = resp.json()

        for config in data["configs"]:
            assert config["id"].startswith("builtin_")

    @pytest.mark.asyncio
    async def test_list_configs_response_schema(self, api_client: AsyncClient):
        """Response has the expected top-level keys."""
        resp = await api_client.get("/api/configs")
        data = resp.json()
        assert set(data.keys()) == {"configs", "builtin_count", "user_count"}


class TestConfigCreate:
    @pytest.mark.asyncio
    async def test_create_config_returns_201(self, api_client: AsyncClient, sample_user_config_data: dict):
        resp = await api_client.post("/api/configs", json=sample_user_config_data)
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_config_assigns_id(self, api_client: AsyncClient, sample_user_config_data: dict):
        resp = await api_client.post("/api/configs", json=sample_user_config_data)
        data = resp.json()

        assert "id" in data
        assert len(data["id"]) > 0  # UUID string

    @pytest.mark.asyncio
    async def test_create_config_sets_source_user(self, api_client: AsyncClient, sample_user_config_data: dict):
        resp = await api_client.post("/api/configs", json=sample_user_config_data)
        data = resp.json()
        assert data["source"] == "user"

    @pytest.mark.asyncio
    async def test_create_config_sets_timestamps(self, api_client: AsyncClient, sample_user_config_data: dict):
        resp = await api_client.post("/api/configs", json=sample_user_config_data)
        data = resp.json()

        assert "created_at" in data
        assert "updated_at" in data
        assert data["created_at"] == data["updated_at"]

    @pytest.mark.asyncio
    async def test_create_config_preserves_fields(self, api_client: AsyncClient, sample_user_config_data: dict):
        resp = await api_client.post("/api/configs", json=sample_user_config_data)
        data = resp.json()

        assert data["name"] == "test_weather_api"
        assert data["description"] == "Get weather for a city"
        assert data["base_url"] == "https://api.weatherapi.com/v1"
        assert data["path"] == "/current.json"
        assert data["method"] == "GET"
        assert data["group_name"] == "Weather"
        assert len(data["parameters"]) == 2

    @pytest.mark.asyncio
    async def test_create_config_appears_in_list(self, api_client: AsyncClient, sample_user_config_data: dict):
        """After creation, the config appears in GET /api/configs."""
        await api_client.post("/api/configs", json=sample_user_config_data)

        resp = await api_client.get("/api/configs")
        data = resp.json()

        assert data["user_count"] == 1
        user_configs = [c for c in data["configs"] if c["source"] == "user"]
        assert len(user_configs) == 1
        assert user_configs[0]["name"] == "test_weather_api"

    @pytest.mark.asyncio
    async def test_create_config_invalid_name_rejected(self, api_client: AsyncClient):
        """Names with invalid characters are rejected by validation."""
        payload = {
            "name": "invalid-name-with-dashes",
            "description": "test",
            "base_url": "https://example.com",
            "path": "/test",
        }
        resp = await api_client.post("/api/configs", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_config_missing_required_fields(self, api_client: AsyncClient):
        """Missing required fields return 422."""
        resp = await api_client.post("/api/configs", json={"name": "test"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_config_empty_name_rejected(self, api_client: AsyncClient):
        """Empty name is rejected."""
        payload = {
            "name": "",
            "description": "test",
            "base_url": "https://example.com",
            "path": "/test",
        }
        resp = await api_client.post("/api/configs", json=payload)
        assert resp.status_code == 422


class TestConfigGetById:
    @pytest.mark.asyncio
    async def test_get_builtin_config(self, api_client: AsyncClient):
        """Can retrieve a built-in config by its ID."""
        resp = await api_client.get("/api/configs/builtin_test_list_posts")
        assert resp.status_code == 200

        data = resp.json()
        assert data["name"] == "test_list_posts"
        assert data["source"] == "builtin"

    @pytest.mark.asyncio
    async def test_get_user_config(self, api_client: AsyncClient, sample_user_config_data: dict):
        """Can retrieve a user config by its ID."""
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        config_id = create_resp.json()["id"]

        resp = await api_client.get(f"/api/configs/{config_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "test_weather_api"

    @pytest.mark.asyncio
    async def test_get_nonexistent_config_returns_404(self, api_client: AsyncClient):
        resp = await api_client.get("/api/configs/does_not_exist")
        assert resp.status_code == 404


class TestConfigUpdate:
    @pytest.mark.asyncio
    async def test_update_user_config(self, api_client: AsyncClient, sample_user_config_data: dict):
        """PUT updates the config and returns the updated version."""
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        config_id = create_resp.json()["id"]

        updated_data = {**sample_user_config_data, "description": "Updated description"}
        resp = await api_client.put(f"/api/configs/{config_id}", json=updated_data)
        assert resp.status_code == 200

        data = resp.json()
        assert data["description"] == "Updated description"
        assert data["id"] == config_id

    @pytest.mark.asyncio
    async def test_update_preserves_created_at(self, api_client: AsyncClient, sample_user_config_data: dict):
        """Update preserves the original created_at timestamp."""
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        original = create_resp.json()
        config_id = original["id"]

        updated_data = {**sample_user_config_data, "description": "Changed"}
        resp = await api_client.put(f"/api/configs/{config_id}", json=updated_data)
        data = resp.json()

        assert data["created_at"] == original["created_at"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_404(self, api_client: AsyncClient, sample_user_config_data: dict):
        resp = await api_client.put("/api/configs/no_such_id", json=sample_user_config_data)
        assert resp.status_code == 404


class TestConfigDelete:
    @pytest.mark.asyncio
    async def test_delete_user_config(self, api_client: AsyncClient, sample_user_config_data: dict):
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        config_id = create_resp.json()["id"]

        resp = await api_client.delete(f"/api/configs/{config_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_removes_from_list(self, api_client: AsyncClient, sample_user_config_data: dict):
        """After deletion, the config no longer appears in listing."""
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        config_id = create_resp.json()["id"]

        await api_client.delete(f"/api/configs/{config_id}")

        resp = await api_client.get("/api/configs")
        assert resp.json()["user_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_builtin_returns_403(self, api_client: AsyncClient):
        """Cannot delete built-in configs."""
        resp = await api_client.delete("/api/configs/builtin_test_list_posts")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, api_client: AsyncClient):
        resp = await api_client.delete("/api/configs/no_such_id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_after_delete_returns_404(self, api_client: AsyncClient, sample_user_config_data: dict):
        """GET by ID returns 404 after the config has been deleted."""
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        config_id = create_resp.json()["id"]

        await api_client.delete(f"/api/configs/{config_id}")

        resp = await api_client.get(f"/api/configs/{config_id}")
        assert resp.status_code == 404


# ── Full CRUD lifecycle ──────────────────────────────────────────────────


class TestConfigLifecycle:
    @pytest.mark.asyncio
    async def test_full_crud_lifecycle(self, api_client: AsyncClient, sample_user_config_data: dict):
        """Test the complete Create → Read → Update → List → Delete → Verify cycle."""
        # 1. Create
        create_resp = await api_client.post("/api/configs", json=sample_user_config_data)
        assert create_resp.status_code == 201
        config_id = create_resp.json()["id"]

        # 2. Read
        get_resp = await api_client.get(f"/api/configs/{config_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "test_weather_api"

        # 3. Update
        updated = {**sample_user_config_data, "description": "Updated weather API", "timeout": 60}
        put_resp = await api_client.put(f"/api/configs/{config_id}", json=updated)
        assert put_resp.status_code == 200
        assert put_resp.json()["description"] == "Updated weather API"
        assert put_resp.json()["timeout"] == 60

        # 4. Verify in list
        list_resp = await api_client.get("/api/configs")
        user_configs = [c for c in list_resp.json()["configs"] if c["source"] == "user"]
        assert len(user_configs) == 1
        assert user_configs[0]["description"] == "Updated weather API"

        # 5. Delete
        del_resp = await api_client.delete(f"/api/configs/{config_id}")
        assert del_resp.status_code == 200

        # 6. Verify gone
        gone_resp = await api_client.get(f"/api/configs/{config_id}")
        assert gone_resp.status_code == 404

        list_resp2 = await api_client.get("/api/configs")
        assert list_resp2.json()["user_count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_user_configs(self, api_client: AsyncClient, sample_user_config_data: dict):
        """Can create multiple user configs; all appear in listing."""
        config1 = {**sample_user_config_data, "name": "api_one"}
        config2 = {**sample_user_config_data, "name": "api_two"}
        config3 = {**sample_user_config_data, "name": "api_three"}

        await api_client.post("/api/configs", json=config1)
        await api_client.post("/api/configs", json=config2)
        await api_client.post("/api/configs", json=config3)

        resp = await api_client.get("/api/configs")
        data = resp.json()
        assert data["user_count"] == 3
        assert data["builtin_count"] == 3

        user_names = {c["name"] for c in data["configs"] if c["source"] == "user"}
        assert user_names == {"api_one", "api_two", "api_three"}
