"""LangGraph agent that uses dynamically registered API tools."""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .config import settings
from .tools.registry import create_tools_from_configs


def create_agent():
    """Create a LangGraph ReAct agent with all registered API tools.

    The agent is equipped with tools dynamically generated from the YAML
    API configurations found in the configured api_config_dir.
    """
    model = ChatOpenAI(model=settings.model_name, api_key=settings.openai_api_key)

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
