"""CRUD routes for API configurations."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..models.api_config import ApiConfigFile, AuthType, HttpMethod, ParameterLocation
from ..storage import ConfigStorage

logger = logging.getLogger(__name__)

router = APIRouter(tags=["configs"])

# Initialize storage
storage = ConfigStorage(settings.user_config_dir)


class ParameterInput(BaseModel):
    name: str
    description: str = ""
    type: str = "string"
    required: bool = False
    location: ParameterLocation = ParameterLocation.QUERY
    default: Any = None


class AuthInput(BaseModel):
    type: AuthType = AuthType.NONE
    token_env_var: str | None = None
    header_name: str = "Authorization"
    prefix: str = "Bearer"


class ApiConfigInput(BaseModel):
    """Input schema for creating/updating an API config."""

    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    description: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    method: HttpMethod = HttpMethod.GET
    parameters: list[ParameterInput] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    auth: AuthInput = Field(default_factory=AuthInput)
    timeout: int = Field(30, ge=1, le=300)
    response_template: str | None = None
    group_name: str = Field("User APIs", description="Group name for organizing tools")


async def _reload_mcp_server() -> None:
    """Signal the MCP server to reload its tool registry."""
    try:
        reload_url = settings.mcp_server_url.replace("/sse", "/reload")
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(reload_url)
            resp.raise_for_status()
            logger.info(f"MCP server reloaded: {resp.json()}")
    except Exception:
        logger.warning("Failed to reload MCP server (it may need manual restart)")


def _load_builtin_configs() -> list[dict[str, Any]]:
    """Load built-in YAML configs and return them as dicts with metadata."""
    from pathlib import Path

    import yaml

    configs = []
    config_path = Path(settings.api_config_dir)

    if not config_path.exists():
        return configs

    for yaml_file in sorted(config_path.glob("*.yaml")):
        try:
            with open(yaml_file) as f:
                raw = yaml.safe_load(f)
            if raw is None:
                continue
            config_file = ApiConfigFile(**raw)
            for group in config_file.groups:
                for api in group.apis:
                    config_dict = api.model_dump()
                    config_dict["id"] = f"builtin_{api.name}"
                    config_dict["source"] = "builtin"
                    config_dict["group_name"] = group.name
                    # Convert enums to strings for JSON serialization
                    config_dict["method"] = api.method.value
                    config_dict["auth"]["type"] = api.auth.type.value
                    for param in config_dict["parameters"]:
                        param["location"] = (
                            param["location"].value if hasattr(param["location"], "value") else param["location"]
                        )
                    configs.append(config_dict)
        except Exception:
            logger.exception(f"Failed to load built-in config from {yaml_file}")

    return configs


@router.get("/configs")
async def list_configs():
    """List all API configs (built-in + user-defined)."""
    builtin = _load_builtin_configs()
    user = storage.list_configs()
    return {
        "configs": builtin + user,
        "builtin_count": len(builtin),
        "user_count": len(user),
    }


@router.get("/configs/{config_id}")
async def get_config(config_id: str):
    """Get a single config by ID."""
    # Check user configs first
    config = storage.get_config(config_id)
    if config:
        return config

    # Check built-in configs
    for cfg in _load_builtin_configs():
        if cfg["id"] == config_id:
            return cfg

    raise HTTPException(status_code=404, detail="Config not found")


@router.post("/configs", status_code=201)
async def create_config(config_input: ApiConfigInput):
    """Create a new user-defined API config."""
    config_data = config_input.model_dump()
    # Convert enums to their values for JSON storage
    config_data["method"] = config_input.method.value
    config_data["auth"]["type"] = config_input.auth.type.value
    for param in config_data["parameters"]:
        param["location"] = param["location"].value if hasattr(param["location"], "value") else param["location"]

    result = storage.save_config(config_data)
    await _reload_mcp_server()
    return result


@router.put("/configs/{config_id}")
async def update_config(config_id: str, config_input: ApiConfigInput):
    """Update an existing user-defined API config."""
    config_data = config_input.model_dump()
    config_data["method"] = config_input.method.value
    config_data["auth"]["type"] = config_input.auth.type.value
    for param in config_data["parameters"]:
        param["location"] = param["location"].value if hasattr(param["location"], "value") else param["location"]

    result = storage.update_config(config_id, config_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Config not found or is a built-in config")

    await _reload_mcp_server()
    return result


@router.delete("/configs/{config_id}")
async def delete_config(config_id: str):
    """Delete a user-defined API config."""
    if config_id.startswith("builtin_"):
        raise HTTPException(status_code=403, detail="Cannot delete built-in configs")

    if not storage.delete_config(config_id):
        raise HTTPException(status_code=404, detail="Config not found")

    await _reload_mcp_server()
    return {"status": "deleted", "id": config_id}
