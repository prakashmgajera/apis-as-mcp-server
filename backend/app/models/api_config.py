"""Pydantic models for REST API configuration that maps to MCP tools."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ParameterLocation(str, Enum):
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    BODY = "body"


class ParameterSchema(BaseModel):
    """Schema for a single API parameter."""

    name: str = Field(..., description="Parameter name")
    description: str = Field("", description="Human-readable description")
    type: str = Field("string", description="Parameter type: string, integer, number, boolean, object, array")
    required: bool = Field(False, description="Whether this parameter is required")
    location: ParameterLocation = Field(ParameterLocation.QUERY, description="Where the parameter is sent")
    default: Any = Field(None, description="Default value if not provided")


class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class AuthConfig(BaseModel):
    """Authentication configuration for an API."""

    type: AuthType = Field(AuthType.NONE)
    token_env_var: str | None = Field(None, description="Environment variable name holding the token/key")
    header_name: str = Field("Authorization", description="Header name for API key auth")
    prefix: str = Field("Bearer", description="Prefix for the auth header value")


class ApiEndpointConfig(BaseModel):
    """Configuration for a single REST API endpoint exposed as an MCP tool."""

    name: str = Field(..., description="Unique tool name (used as the MCP tool identifier)")
    description: str = Field(..., description="Human-readable description of what this API does")
    base_url: str = Field(..., description="Base URL of the API (can use env vars like ${API_HOST})")
    path: str = Field(..., description="URL path (supports path params like /users/{user_id})")
    method: HttpMethod = Field(HttpMethod.GET)
    parameters: list[ParameterSchema] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict, description="Static headers to include")
    auth: AuthConfig = Field(default_factory=AuthConfig)
    timeout: int = Field(30, description="Request timeout in seconds")
    response_template: str | None = Field(
        None,
        description="Optional Jinja2 template to format the response for the LLM",
    )


class ApiGroupConfig(BaseModel):
    """A group of related API endpoints."""

    name: str = Field(..., description="Group name")
    description: str = Field("", description="Group description")
    apis: list[ApiEndpointConfig] = Field(default_factory=list)


class ApiConfigFile(BaseModel):
    """Root configuration file schema."""

    version: str = Field("1.0")
    groups: list[ApiGroupConfig] = Field(default_factory=list)
