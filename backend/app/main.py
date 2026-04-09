"""FastAPI application with CopilotKit runtime integration."""

from __future__ import annotations

import logging

from copilotkit import CopilotKitRemoteEndpoint, LangGraphAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.on_event("startup")
async def startup():
    """Initialize the agent and CopilotKit endpoint on startup."""
    from .agent import create_agent

    try:
        agent = create_agent()

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
        logger.info("CopilotKit agent initialized successfully")
    except Exception:
        logger.exception("Failed to initialize agent — /copilotkit will not be available")


@app.get("/health")
async def health():
    return {"status": "healthy", "app": settings.app_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
