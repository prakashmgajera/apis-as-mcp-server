"""Tool registry that loads API configurations and creates LangChain tools."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from ..models.api_config import ApiConfigFile, ApiEndpointConfig
from .api_tool import execute_api_call

logger = logging.getLogger(__name__)

# Map config type strings to Python types
TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def _build_args_model(config: ApiEndpointConfig) -> type[BaseModel]:
    """Dynamically create a Pydantic model for the tool's input arguments."""
    fields: dict[str, Any] = {}

    for param in config.parameters:
        python_type = TYPE_MAP.get(param.type, str)

        if param.required:
            fields[param.name] = (
                python_type,
                Field(description=param.description or param.name),
            )
        else:
            fields[param.name] = (
                python_type | None,
                Field(default=param.default, description=param.description or param.name),
            )

    if not fields:
        fields["_placeholder"] = (
            str | None,
            Field(default=None, description="No parameters required"),
        )

    model = create_model(f"{config.name}_Args", **fields)
    return model


def _create_tool(config: ApiEndpointConfig) -> StructuredTool:
    """Create a LangChain StructuredTool from an API endpoint config."""
    args_model = _build_args_model(config)

    # Filter out path params from the description since they're part of the URL
    param_descriptions = []
    for param in config.parameters:
        req = "required" if param.required else "optional"
        param_descriptions.append(f"  - {param.name} ({req}): {param.description}")

    description = config.description
    if param_descriptions:
        description += "\n\nParameters:\n" + "\n".join(param_descriptions)

    async def _run(**kwargs: Any) -> str:
        # Remove placeholder if present
        kwargs.pop("_placeholder", None)
        return await execute_api_call(config, **kwargs)

    return StructuredTool(
        name=config.name,
        description=description,
        args_schema=args_model,
        coroutine=_run,
    )


def load_api_configs(config_dir: str) -> list[ApiEndpointConfig]:
    """Load all API configurations from YAML files in the given directory."""
    configs: list[ApiEndpointConfig] = []
    config_path = Path(config_dir)

    if not config_path.exists():
        logger.warning(f"API config directory does not exist: {config_dir}")
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
                logger.info(f"Loaded {len(group.apis)} APIs from group '{group.name}' in {yaml_file.name}")

        except Exception:
            logger.exception(f"Failed to load API config from {yaml_file}")

    return configs


def create_tools_from_configs(config_dir: str) -> list[StructuredTool]:
    """Load all API configs and create LangChain tools from them."""
    endpoint_configs = load_api_configs(config_dir)
    tools: list[StructuredTool] = []

    for config in endpoint_configs:
        try:
            tool = _create_tool(config)
            tools.append(tool)
            logger.info(f"Created tool: {config.name}")
        except Exception:
            logger.exception(f"Failed to create tool for: {config.name}")

    logger.info(f"Total tools created: {len(tools)}")
    return tools
