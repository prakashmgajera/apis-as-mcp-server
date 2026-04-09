"""LangGraph agent that uses dynamically registered API tools."""

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from .config import settings
from .tools.registry import create_tools_from_configs

logger = logging.getLogger(__name__)

SYSTEM_MESSAGE = (
    "You are a helpful assistant that can interact with various REST APIs on behalf of the user. "
    "You have access to the following API tools. Use them to fulfill user requests.\n\n"
    "Guidelines:\n"
    "- Always confirm what the user wants before making destructive API calls (DELETE, PUT).\n"
    "- Present API responses in a clear, human-readable format.\n"
    "- If an API call fails, explain the error and suggest next steps.\n"
    "- When multiple API calls are needed, plan the sequence and explain your approach.\n"
)


def _create_model(provider: str, model_name: str, api_key: str) -> BaseChatModel:
    """Create the chat model for the given provider."""
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model_name, api_key=api_key)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model_name, api_key=api_key)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)

    raise ValueError(f"Unsupported model provider: {provider}")


def create_agent(
    provider: str = "",
    model_name: str = "",
    api_key: str = "",
):
    """Create a LangGraph ReAct agent with all registered API tools.

    When called without arguments, falls back to settings from environment.
    When called with explicit provider/model_name/api_key, uses those instead
    (for per-request session-based configuration).
    """
    provider = provider or settings.model_provider.value
    model_name = model_name or settings.model_name

    logger.info(f"Creating agent with provider={provider}, model={model_name}")

    model = _create_model(provider, model_name, api_key)
    tools = create_tools_from_configs(settings.api_config_dir)

    # Use state_modifier for broad LangGraph >=0.2 compatibility.
    # (Renamed to 'prompt' in later versions, but state_modifier still works.)
    agent = create_react_agent(
        model=model,
        tools=tools,
        state_modifier=SYSTEM_MESSAGE,
    )

    return agent
