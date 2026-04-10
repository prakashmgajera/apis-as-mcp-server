"""LangGraph agent that uses MCP tools from the MCP Server."""

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AnyMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent

from .config import settings

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
    selected_tools: list[str] | None = None,
):
    """Create a LangGraph agent that connects to the MCP Server for tools.

    The returned graph manages the MCP client lifecycle internally:
    it connects to the MCP server, fetches tools, optionally filters them,
    and runs the ReAct agent loop.
    """
    provider = provider or settings.model_provider.value
    model_name = model_name or settings.model_name

    logger.info(f"Creating agent with provider={provider}, model={model_name}")

    model = _create_model(provider, model_name, api_key)
    mcp_server_url = settings.mcp_server_url

    async def agent_node(state: MessagesState) -> dict[str, list[AnyMessage]]:
        """Run the ReAct agent with MCP tools fetched from the MCP server."""
        mcp_client = MultiServerMCPClient(
            {
                "api-tools": {
                    "transport": "sse",
                    "url": mcp_server_url,
                    "timeout": 30,
                    "sse_read_timeout": 300,
                },
            }
        )
        tools = await mcp_client.get_tools()

        # Filter to selected tools if specified
        if selected_tools:
            tools = [t for t in tools if t.name in selected_tools]
            logger.info(f"Filtered to {len(tools)} tools: {[t.name for t in tools]}")
        else:
            logger.info(f"Using all {len(tools)} MCP tools")

        inner_agent = create_react_agent(
            model=model,
            tools=tools,
            state_modifier=SYSTEM_MESSAGE,
        )

        result = await inner_agent.ainvoke(state)
        return {"messages": result["messages"]}

    # Build a simple graph wrapper so CopilotKit gets a CompiledStateGraph
    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    graph.set_finish_point("agent")

    return graph.compile()
