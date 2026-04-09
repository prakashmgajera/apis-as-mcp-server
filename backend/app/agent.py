"""LangGraph agent that uses dynamically registered API tools."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from .config import ModelProvider, settings
from .tools.registry import create_tools_from_configs


def _create_model() -> BaseChatModel:
    """Create the chat model based on the configured provider."""
    if settings.model_provider == ModelProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.model_name, api_key=settings.openai_api_key)

    if settings.model_provider == ModelProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=settings.model_name, api_key=settings.anthropic_api_key)

    if settings.model_provider == ModelProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=settings.model_name, google_api_key=settings.google_api_key)

    raise ValueError(f"Unsupported model provider: {settings.model_provider}")


def create_agent():
    """Create a LangGraph ReAct agent with all registered API tools.

    The agent is equipped with tools dynamically generated from the YAML
    API configurations found in the configured api_config_dir.
    """
    model = _create_model()

    tools = create_tools_from_configs(settings.api_config_dir)

    system_message = (
        "You are a helpful assistant that can interact with various REST APIs on behalf of the user. "
        "You have access to the following API tools. Use them to fulfill user requests.\n\n"
        "Guidelines:\n"
        "- Always confirm what the user wants before making destructive API calls (DELETE, PUT).\n"
        "- Present API responses in a clear, human-readable format.\n"
        "- If an API call fails, explain the error and suggest next steps.\n"
        "- When multiple API calls are needed, plan the sequence and explain your approach.\n"
    )

    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=system_message,
    )

    return agent
