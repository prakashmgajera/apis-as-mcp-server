"""FastAPI application with CopilotKit runtime integration."""

from __future__ import annotations

import logging

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.graph import MessagesState, StateGraph

from .agent import create_agent
from .config import settings

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Turn your REST APIs into chat-accessible MCP tools powered by CopilotKit",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _create_placeholder_agent():
    """Create a minimal LangGraph agent so the /info endpoint can register the agent name.

    This placeholder is swapped for the real agent on each chat request.
    """
    graph = StateGraph(MessagesState)
    graph.add_node("noop", lambda state: state)
    graph.set_entry_point("noop")
    graph.set_finish_point("noop")
    return graph.compile()


# Register a placeholder so CopilotKit /info returns "api_agent".
# The real agent (with the user's API key) is injected per-request via middleware.
copilotkit_sdk = CopilotKitRemoteEndpoint(
    agents=[
        LangGraphAgent(
            name="api_agent",
            description="An agent that can interact with configured REST APIs to help users accomplish tasks.",
            agent=_create_placeholder_agent(),
        ),
    ],
)
add_fastapi_endpoint(app, copilotkit_sdk, "/copilotkit")


@app.middleware("http")
async def inject_model_from_headers(request: Request, call_next):
    """Create the LLM agent per request using model config from headers.

    The API key is used only for this request and never persisted.
    """
    if "/copilotkit" in request.url.path and request.method == "POST":
        provider = request.headers.get("x-model-provider", settings.model_provider.value)
        model_name = request.headers.get("x-model-name", settings.model_name)
        api_key = request.headers.get("x-api-key", "")

        # Fall back to env-var keys when no header key is provided
        if not api_key:
            key_map = {
                "openai": settings.openai_api_key,
                "anthropic": settings.anthropic_api_key,
                "google": settings.google_api_key,
            }
            api_key = key_map.get(provider, "")

        if not api_key:
            return JSONResponse(
                status_code=400,
                content={"error": "API key is required. Please configure your model provider."},
            )

        try:
            agent = create_agent(provider=provider, model_name=model_name, api_key=api_key)
            copilotkit_sdk.agents = [
                LangGraphAgent(
                    name="api_agent",
                    description="An agent that can interact with configured REST APIs to help users accomplish tasks.",
                    agent=agent,
                )
            ]
        except Exception as e:
            logger.exception("Failed to create agent from request headers")
            return JSONResponse(
                status_code=500,
                content={"error": f"Failed to initialize model: {e}"},
            )

    return await call_next(request)


@app.get("/health")
async def health():
    return {"status": "healthy", "app": settings.app_name}


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", settings.port))
    uvicorn.run(app, host="0.0.0.0", port=port)
