# APIs as MCP Server

Turn your REST APIs into chat-accessible tools. Define APIs in simple YAML files, and interact with them through a conversational chat interface powered by [CopilotKit](https://copilotkit.ai) and LangGraph.

## How It Works

```
YAML API Config  -->  Python Backend  -->  CopilotKit Chat UI
(your APIs)          (LangGraph Agent)     (Next.js frontend)
```

1. **Define** your REST APIs as YAML configuration files
2. **Backend** dynamically converts them into LangChain tools and serves a LangGraph agent via CopilotKit
3. **Frontend** provides a chat interface where users interact with those APIs conversationally

## Architecture

```
├── backend/                   # Python (FastAPI + CopilotKit + LangGraph)
│   ├── app/
│   │   ├── main.py            # FastAPI server with CopilotKit runtime
│   │   ├── agent.py           # LangGraph ReAct agent
│   │   ├── config.py          # App configuration
│   │   ├── models/
│   │   │   └── api_config.py  # Pydantic models for API definitions
│   │   └── tools/
│   │       ├── registry.py    # Loads YAML configs, creates LangChain tools
│   │       └── api_tool.py    # Executes HTTP requests for each tool
│   └── api_configs/           # Your API definitions go here
│       ├── example_apis.yaml
│       └── authenticated_api_example.yaml
│
├── frontend/                  # Next.js + CopilotKit
│   └── src/app/
│       ├── layout.tsx         # CopilotKit provider setup
│       └── page.tsx           # Chat interface
│
└── docker-compose.yml
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- An OpenAI API key

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local

# Start the dev server
npm run dev
```

### 3. Open the Chat

Navigate to [http://localhost:3000](http://localhost:3000) and start chatting with your APIs.

### Docker (Alternative)

```bash
# Copy and configure env files first
cp backend/.env.example backend/.env
# Edit backend/.env with your OPENAI_API_KEY

docker compose up --build
```

## Defining Your APIs

Create YAML files in `backend/api_configs/` to register your REST APIs as chat tools. Each API endpoint becomes a tool the AI agent can invoke.

### Basic Example

```yaml
version: "1.0"

groups:
  - name: My Service
    description: APIs for my service

    apis:
      - name: get_items
        description: "Retrieve a list of items"
        base_url: "https://api.myservice.com"
        path: "/items"
        method: GET
        parameters:
          - name: category
            description: "Filter by category"
            type: string
            required: false
            location: query
```

### With Authentication

```yaml
apis:
  - name: create_ticket
    description: "Create a support ticket"
    base_url: "https://api.myservice.com"
    path: "/tickets"
    method: POST
    auth:
      type: bearer
      token_env_var: MY_SERVICE_TOKEN  # reads from environment
    parameters:
      - name: title
        description: "Ticket title"
        type: string
        required: true
        location: body
      - name: priority
        description: "Priority level: low, medium, high"
        type: string
        required: false
        location: body
        default: "medium"
```

### With Path Parameters

```yaml
apis:
  - name: get_order
    description: "Get order details by ID"
    base_url: "${API_HOST}"  # env var substitution
    path: "/orders/{orderId}"
    method: GET
    parameters:
      - name: orderId
        description: "The order ID"
        type: integer
        required: true
        location: path
```

### With Response Templates

```yaml
apis:
  - name: search_products
    description: "Search product catalog"
    base_url: "https://api.store.com"
    path: "/products/search"
    method: GET
    parameters:
      - name: q
        description: "Search query"
        type: string
        required: true
        location: query
    response_template: |
      Found {{ response.total }} products:
      {% for item in response.items[:5] %}
      - {{ item.name }} (${{ item.price }}): {{ item.description }}
      {% endfor %}
```

### Configuration Reference

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique tool identifier |
| `description` | string | What this API does (shown to the LLM) |
| `base_url` | string | API base URL (supports `${ENV_VAR}` syntax) |
| `path` | string | URL path (supports `{param}` placeholders) |
| `method` | string | HTTP method: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `parameters` | list | Parameter definitions (see below) |
| `headers` | dict | Static headers to include |
| `auth` | object | Authentication config |
| `timeout` | integer | Request timeout in seconds (default: 30) |
| `response_template` | string | Jinja2 template to format the response |

**Parameter fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Parameter name |
| `description` | string | Human-readable description |
| `type` | string | `string`, `integer`, `number`, `boolean`, `object`, `array` |
| `required` | boolean | Whether this parameter is required |
| `location` | string | `query`, `path`, `header`, `body` |
| `default` | any | Default value if not provided |

**Auth types:**

| Type | Fields | Description |
|------|--------|-------------|
| `none` | - | No authentication |
| `bearer` | `token_env_var`, `prefix` | Bearer token auth |
| `api_key` | `token_env_var`, `header_name` | API key in custom header |
| `basic` | `token_env_var` | HTTP Basic auth |

## Deploy to Railway

Railway lets you deploy both services directly from your GitHub repo.

### Step 1: Create a Railway Project

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **New Project** → **Empty Project**

### Step 2: Deploy the Backend

1. In your project, click **New** → **GitHub Repo** → select this repo
2. Railway will detect the repo — click **Add Service**
3. Go to the service **Settings**:
   - Set **Root Directory** to `backend`
   - Set **Start Command** to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Go to **Variables** and add:
   ```
   MODEL_PROVIDER=openai          # or anthropic, google
   MODEL_NAME=gpt-4o              # or claude-sonnet-4-20250514, gemini-2.0-flash
   OPENAI_API_KEY=sk-...          # key for your chosen provider
   ```
5. Go to **Settings** → **Networking** → click **Generate Domain** (note the URL)

### Step 3: Deploy the Frontend

1. In the same project, click **New** → **GitHub Repo** → select this repo again
2. Go to the service **Settings**:
   - Set **Root Directory** to `frontend`
3. Go to **Variables** and add:
   ```
   NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL=https://<your-backend>.up.railway.app/copilotkit
   ```
4. Go to **Settings** → **Networking** → click **Generate Domain**

### Step 4: Open and Chat

Visit your frontend domain — the chat interface is ready to use.

> **Tip:** Both services auto-redeploy when you push to the connected branch. Add new YAML API configs, push, and they're live.

## Tech Stack

- **Backend:** Python, FastAPI, LangGraph, LangChain, CopilotKit Python SDK
- **Frontend:** Next.js, React, CopilotKit React UI, Tailwind CSS
- **Protocol:** CopilotKit Runtime (agent communication)

## License

MIT
