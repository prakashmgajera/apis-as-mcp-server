"""Load API configurations and convert them to MCP tool definitions."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from app.models.api_config import ApiConfigFile, ApiEndpointConfig, ParameterLocation
from app.tools.api_tool import execute_api_call

logger = logging.getLogger(__name__)

# Map config type strings to JSON Schema types
JSON_SCHEMA_TYPE_MAP: dict[str, str] = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "object": "object",
    "array": "array",
}


class ToolRegistry:
    """Manages API configs and provides MCP tool schemas + execution."""

    def __init__(self, builtin_config_dir: str, user_config_dir: str | None = None):
        self.builtin_config_dir = builtin_config_dir
        self.user_config_dir = user_config_dir
        self._configs: dict[str, ApiEndpointConfig] = {}
        self.reload()

    def reload(self) -> None:
        """Reload all configs from disk."""
        self._configs.clear()

        # Load built-in YAML configs
        for config in self._load_yaml_configs(self.builtin_config_dir):
            self._configs[config.name] = config

        # Load user-defined JSON configs
        if self.user_config_dir:
            for config in self._load_user_configs(self.user_config_dir):
                self._configs[config.name] = config

        logger.info(f"ToolRegistry loaded {len(self._configs)} tools")

    def _load_yaml_configs(self, config_dir: str) -> list[ApiEndpointConfig]:
        """Load API configurations from YAML files."""
        configs: list[ApiEndpointConfig] = []
        config_path = Path(config_dir)

        if not config_path.exists():
            logger.warning(f"Config directory does not exist: {config_dir}")
            return configs

        for yaml_file in sorted(config_path.glob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    raw = yaml.safe_load(f)
                if raw is None:
                    continue
                config_file = ApiConfigFile(**raw)
                for group in config_file.groups:
                    configs.extend(group.apis)
                    logger.info(
                        f"Loaded {len(group.apis)} APIs from group '{group.name}' in {yaml_file.name}"
                    )
            except Exception:
                logger.exception(f"Failed to load YAML config from {yaml_file}")

        return configs

    def _load_user_configs(self, config_dir: str) -> list[ApiEndpointConfig]:
        """Load user-defined API configurations from JSON files."""
        configs: list[ApiEndpointConfig] = []
        config_path = Path(config_dir)

        if not config_path.exists():
            return configs

        for json_file in sorted(config_path.glob("*.json")):
            try:
                with open(json_file) as f:
                    raw = json.load(f)
                config = ApiEndpointConfig(**raw)
                configs.append(config)
                logger.info(f"Loaded user config: {config.name} from {json_file.name}")
            except Exception:
                logger.exception(f"Failed to load user config from {json_file}")

        return configs

    def get_tool_names(self) -> list[str]:
        """Return all registered tool names."""
        return list(self._configs.keys())

    def get_config(self, tool_name: str) -> ApiEndpointConfig | None:
        """Get the config for a specific tool."""
        return self._configs.get(tool_name)

    def get_all_configs(self) -> list[ApiEndpointConfig]:
        """Return all registered configs."""
        return list(self._configs.values())

    def build_input_schema(self, config: ApiEndpointConfig) -> dict[str, Any]:
        """Build a JSON Schema object for the tool's input parameters."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in config.parameters:
            prop: dict[str, Any] = {
                "type": JSON_SCHEMA_TYPE_MAP.get(param.type, "string"),
            }
            if param.description:
                prop["description"] = param.description
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required

        return schema

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute an API call for the named tool. Returns formatted response text."""
        config = self._configs.get(tool_name)
        if config is None:
            return f"Error: Unknown tool '{tool_name}'"
        return await execute_api_call(config, **arguments)
