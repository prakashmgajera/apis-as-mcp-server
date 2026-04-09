"""Application configuration."""

from __future__ import annotations

import os
from enum import Enum

from pydantic_settings import BaseSettings


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "APIs as MCP Server"
    debug: bool = False

    # LLM Provider
    model_provider: ModelProvider = ModelProvider.OPENAI
    model_name: str = "gpt-4o"

    # Provider API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # API config directory
    api_config_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api_configs")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
