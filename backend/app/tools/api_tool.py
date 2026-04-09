"""Dynamic tool creator that converts REST API configs into LangChain tools."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from ..models.api_config import (
    ApiEndpointConfig,
    AuthType,
    HttpMethod,
    ParameterLocation,
)


def _resolve_env_vars(value: str) -> str:
    """Replace ${ENV_VAR} placeholders with actual environment variable values."""

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(r"\$\{(\w+)}", replacer, value)


def _build_auth_headers(config: ApiEndpointConfig) -> dict[str, str]:
    """Build authentication headers based on the auth config."""
    headers: dict[str, str] = {}
    auth = config.auth

    if auth.type == AuthType.NONE:
        return headers

    token = ""
    if auth.token_env_var:
        token = os.environ.get(auth.token_env_var, "")

    if auth.type == AuthType.BEARER:
        headers["Authorization"] = f"{auth.prefix} {token}"
    elif auth.type == AuthType.API_KEY:
        headers[auth.header_name] = token
    elif auth.type == AuthType.BASIC:
        import base64

        headers["Authorization"] = f"Basic {base64.b64encode(token.encode()).decode()}"

    return headers


async def execute_api_call(config: ApiEndpointConfig, **kwargs: Any) -> str:
    """Execute an API call based on the endpoint configuration and provided arguments.

    Returns the response as a formatted string suitable for LLM consumption.
    """
    # Resolve environment variables in base_url
    base_url = _resolve_env_vars(config.base_url)
    path = config.path

    # Separate parameters by location
    query_params: dict[str, Any] = {}
    body_params: dict[str, Any] = {}
    header_params: dict[str, str] = {}

    for param in config.parameters:
        value = kwargs.get(param.name, param.default)
        if value is None:
            continue

        if param.location == ParameterLocation.PATH:
            path = path.replace(f"{{{param.name}}}", str(value))
        elif param.location == ParameterLocation.QUERY:
            query_params[param.name] = value
        elif param.location == ParameterLocation.HEADER:
            header_params[param.name] = str(value)
        elif param.location == ParameterLocation.BODY:
            body_params[param.name] = value

    # Build headers
    headers = {**config.headers}
    headers.update(_build_auth_headers(config))
    headers.update(header_params)

    # Resolve env vars in static headers
    headers = {k: _resolve_env_vars(v) for k, v in headers.items()}

    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    async with httpx.AsyncClient(timeout=config.timeout) as client:
        request_kwargs: dict[str, Any] = {
            "method": config.method.value,
            "url": url,
            "headers": headers,
            "params": query_params if query_params else None,
        }

        if config.method in (HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH) and body_params:
            request_kwargs["json"] = body_params

        response = await client.request(**request_kwargs)

    # Format the response
    try:
        data = response.json()
        if config.response_template:
            from jinja2 import Template

            template = Template(config.response_template)
            return template.render(response=data, status_code=response.status_code)
        return json.dumps(data, indent=2)
    except (json.JSONDecodeError, ValueError):
        return f"Status: {response.status_code}\n\n{response.text[:2000]}"
