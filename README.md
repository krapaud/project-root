# HBntory — Inventory Management System

Multi-branch retail inventory system: an authenticated Backoffice for stock
and user management, an external read-only Product API, an MCP server
bridging product data to an AI agent, an independent AI Query Service, and a
public natural-language Client Web Interface.

## Documentation

- [Architecture](docs/architecture.md) — services, responsibilities, data
  flow, and how the AI agent accesses product/stock data.
- [Communication Decisions](docs/communication-decisions.md) — REST vs SSR,
  REST vs WebSockets, AI service ↔ MCP, AI service ↔ stock data.
- [MVP Definition](docs/mvp.md) — build order and what's explicitly deferred.
- [Database Schema](docs/database-schema.md) — tables, constraints, why no
  local `products` table.
- [Validation Rules](docs/validation-rules.md) — stock validation rules and
  where they're enforced.
- [Authentication & Authorization](docs/auth.md) — session strategy,
  password hashing, role enforcement.
- [Product MCP Server](docs/mcp-server.md) — tools exposed, error handling,
  manual test evidence.
- [AI Query Service](docs/ai-query-service.md) — supported question types,
  agent/MCP wiring, manual test evidence.

## Client Web Interface — Example Questions

The public page at `client_web/index.html` accepts free-text questions.
Supported question types, with examples verified against the running
system:

- **Product details**: "Give me details about product prod-001."
- **Where a product is available**: "Which branch has stock of prod-001?"
- **What's in a branch**: "What products can I find in branch 1?"
- **Shopping-list recommendation**: "If I want to buy 3 units of prod-001
  and 2 units of prod-002, which branch or branches should I visit?"

Anything else, or a question about an unknown product/branch, gets an
explicit "not available" answer rather than an invented one.

## Setup & Running Each Service

Each service has its own virtualenv and `.env.example`. Run
`cp .env.example .env` in each before starting it.

### 1. External Product API (stub for local dev)

The real Product API is provided as a Docker container per the project
spec. For local development without it, any stub exposing
`GET /products` and `GET /products/{id}` (404 on unknown id) works — this
is what was used for all manual testing referenced in the docs above.

### 2. Backoffice

```bash
cd backoffice
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m scripts.seed        # creates admin user, 2 branches, sample stock
uvicorn app.main:app --port 8000
```

Visit `http://localhost:8000/login`. Default seeded admin credentials are
printed by the seed script (override via `SEED_ADMIN_PASSWORD`).

### 3. Product MCP Server

```bash
cd product_mcp_server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 test_client.py   # manual tool test (see docs/mcp-server.md)
```

Normally launched as a subprocess by `ai_service`, not run standalone.

### 4. AI Query Service

```bash
cd ai_service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama pull qwen2.5-coder:7b   # or the model set in .env
uvicorn app.main:app --port 9000
```

Requires `product_mcp_server`'s own `.venv` to already exist (see above) —
it's launched as a subprocess, not imported.

### 5. Client Web Interface

```bash
cd client_web
python3 -m http.server 5500
```

Visit `http://localhost:5500/index.html`. Update `AI_SERVICE_URL` in
`app.js` if `ai_service` runs on a different host/port.

## Known Limitations

- Local model tool-use reliability varies: `llama3.2:1b` produced malformed
  tool calls; `qwen2.5-coder:7b` is the validated default (see
  `docs/ai-query-service.md`).
- No automated test suite yet beyond the manual scenarios documented per
  service.
- Services are not yet containerized (`docker-compose.yml` deferred per
  `docs/mvp.md`).

## Status

Tasks 0–6 implemented and manually verified end-to-end. Task 7
(integration/testing/docs polish) and Task 8 (presentation) remain.
