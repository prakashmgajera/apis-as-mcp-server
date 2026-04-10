# CLAUDE.md

## Project Overview

Monorepo that converts REST APIs (defined in YAML) into conversational chat tools using MCP, CopilotKit, LangGraph, and FastAPI. Three services: MCP server (port 8001), FastAPI backend (port 8000), Next.js frontend (port 3000).

## Build & Run Commands

### Backend (Python 3.11+, working directory: `backend/`)
```bash
pip install -e ".[dev]"                 # Install with dev dependencies
uvicorn app.main:app --reload --port 8000  # Run backend
python -m mcp_server.run               # Run MCP server standalone
```

### Frontend (Node.js, working directory: `frontend/`)
```bash
npm install                             # Install dependencies
npm run dev                             # Dev server with Turbopack
npm run build                           # Production build
```

### Docker
```bash
docker compose up --build               # All three services
```

## Testing

### Backend tests (run from `backend/`)
```bash
pytest                                  # Run all tests
pytest tests/test_mcp_server.py         # Run single test file
pytest tests/test_fastapi_routes.py -k test_name  # Run single test
```
- Uses pytest with `asyncio_mode = "auto"` — no need for `@pytest.mark.asyncio`
- Test fixtures in `tests/conftest.py` create temp config dirs and patch settings
- Prefer running single test files over the full suite for speed

### Frontend
```bash
npm run lint                            # ESLint via Next.js
npx tsc --noEmit                        # Type checking
```

## Linting & Formatting

### Backend
```bash
ruff check backend/                     # Lint
ruff check backend/ --fix               # Lint with auto-fix
ruff format backend/                    # Format
```

### Frontend
```bash
cd frontend && npm run lint             # Next.js ESLint
```

IMPORTANT: Always run the relevant linter after making code changes. Run type checking (`npx tsc --noEmit` in `frontend/`) after modifying TypeScript files.

## Code Style

### Python (backend)
- Use `from __future__ import annotations` at top of every module
- Pydantic v2 models for data validation (see `app/models/api_config.py` for patterns)
- Pydantic Settings for configuration (`app/config.py`)
- Type hints on all function signatures
- Use `httpx` for async HTTP requests (not `requests`)
- Use `logging` module, not print statements

### TypeScript (frontend)
- ES modules with named imports
- Path alias `@/*` maps to `./src/*`
- React 19 + Next.js 15 App Router (all routes under `src/app/`)
- Tailwind CSS for styling — no CSS modules
- CopilotKit hooks (`useCoAgent`) for chat integration
- API proxy routes in `src/app/api/` to avoid CORS issues

## Architecture

- **`backend/app/`** — FastAPI application: routes, middleware, agent creation
- **`backend/mcp_server/`** — Standalone MCP server that loads YAML configs and registers tools
- **`backend/app/agent.py`** — LangGraph ReAct agent creation, supports OpenAI/Anthropic/Google
- **`backend/app/routes/`** — REST endpoints for config CRUD and tool listing
- **`backend/api_configs/`** — Built-in YAML API definitions
- **`frontend/src/components/`** — React components (ConfigPanel, ChatAgent, ApiConfigBuilder, etc.)
- **`frontend/src/app/api/`** — Next.js API proxy routes to backend

## Environment Variables

- Copy `backend/.env.example` to `backend/.env` and set at minimum one LLM provider API key
- Copy `frontend/.env.example` to `frontend/.env`
- NEVER commit `.env` files — they contain API keys
- YAML configs can reference env vars with `${VAR_NAME}` syntax

## Common Gotchas

- `app/main.py` has two monkey-patches for CopilotKit SDK compatibility — do not remove them without testing the full chat flow
- The MCP server must be running before the backend starts (see `docker-compose.yml` dependency chain)
- Backend tests patch `app.config.settings` directly — do not rely on env vars in tests
- Frontend proxy routes (`src/app/api/backend/` and `src/app/api/copilotkit/`) forward headers including `x-model-provider`, `x-api-key`, and `x-selected-tools`
