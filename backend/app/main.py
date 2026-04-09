"""FastAPI application with CopilotKit runtime integration."""

from __future__ import annotations

import logging

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Create the LangGraph agent with dynamically loaded API tools
agent = create_agent()

# Set up CopilotKit remote endpoint with the agent
copilotkit = CopilotKitRemoteEndpoint(
    agents=[
        LangGraphAgent(
            name="api_agent",
            description="An agent that can interact with configured REST APIs to help users accomplish tasks.",
            agent=agent,
        ),
    ],
)

add_fastapi_endpoint(app, copilotkit, "/copilotkit")


@app.get("/health")
async def health():
    return {"status": "healthy", "app": settings.app_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
