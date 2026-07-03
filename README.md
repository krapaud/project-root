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
- [Test Evidence](docs/test-evidence.md) — automated test results, critical
  scenario coverage, full-system integration run.

## Client Web Interface — Example Questions

The public page at `client_web/index.html` accepts free-text questions.
Supported question types, with examples verified against the running
system:

- **Product details**: "Give me details about product HB-LAP-1001."
- **Where a product is available**: "Which branch has stock of HB-LAP-1001?"
- **What's in a branch**: "What products can I find in branch 1?"
- **Shopping-list recommendation**: "If I want to buy 3 units of HB-LAP-1001
  and 2 units of HB-KEY-2002, which branch or branches should I visit?"

Anything else, or a question about an unknown product/branch, gets an
explicit "not available" answer rather than an invented one.

## Setup & Running Each Service

Each service has its own virtualenv and `.env.example`. Run
`cp .env.example .env` in each before starting it.

### 1. External Product API

Provided as a Docker container:
[hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api).
Clone it and run `docker compose up --build`; it serves on
`http://localhost:5001` (`GET /health`, `GET /api/v1/products`,
`GET /api/v1/products/{id_or_sku}`, etc. — full contract in that repo's
`docs/api_contract.md`). `product_id` throughout HBntory is this API's
**SKU** field (e.g. `HB-LAP-1001`), not its numeric `id`.

For local development without the real container, any stub exposing the
same two endpoints (list + `{id_or_sku}` detail, 404 with
`{"error": "not_found", "message": "..."}` on an unknown SKU) works — this
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

## Running the Tests

```bash
cd backoffice
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

23 automated tests cover stock validation, user management, authentication,
and role-based authorization (including at the HTTP route level). AI Query
Service and MCP server behavior is covered by documented manual test runs
(no automated tests, since correctness there depends on a live LLM) — see
`docs/test-evidence.md` for the full critical-scenario mapping and a
recorded full-system integration run touching all five services in
sequence.

## Known Limitations

- Local model tool-use reliability varies: `llama3.2:1b` produced malformed
  tool calls; `qwen2.5-coder:7b` is the validated default (see
  `docs/ai-query-service.md`).
- No automated tests for the AI Query Service or MCP server — covered by
  documented manual runs instead, since they depend on a live LLM/Ollama
  and an external Product API.
- Services are not yet containerized (`docker-compose.yml` deferred per
  `docs/mvp.md`); each service runs from its own virtualenv.
- Testing used a lightweight stub Product API, not the real Docker
  container (not available in this environment) — see `docs/test-evidence.md`.

## Status

Tasks 0–7 implemented and verified: architecture, database, backoffice
auth/authorization, backoffice stock and user management, Product MCP
Server, AI Query Service, Client Web Interface, automated tests, and a
full-system integration run. Task 8 (final presentation) remains.
