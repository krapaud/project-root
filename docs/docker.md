# Running HBntory with Docker Compose

## Overview

`docker-compose.yml` at the repo root runs four of the five HBntory
services as containers, plus a PostgreSQL database:

| Service | Container port | Host port | Notes |
|---|---|---|---|
| `db` | 5432 | (none published) | PostgreSQL 16, only reachable by other containers on the compose network |
| `backoffice` | 8000 | **8010** | Port shifted to avoid clashing with other projects' `8000` on the host |
| `product_mcp_server` | 8100 | 8100 | Runs in HTTP transport mode (`MCP_TRANSPORT=http`) instead of stdio |
| `ai_service` | 9000 | 9000 | Connects to `product_mcp_server` over HTTP, not as a local subprocess |
| `client_web` | 80 | 5500 | Served by nginx |

**Not containerized**: the external Product API
([hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api))
and Ollama. Both are expected to already be running on the host machine —
containers reach them via `host.docker.internal` (Docker's bridge back to
the host), configured through `extra_hosts` in the compose file. This
mirrors the architecture decision that the Product API is an externally
provided component, not something this team builds or packages.

## Why a Transport Change Was Needed

Outside Docker, `ai_service` launches `product_mcp_server` as a **local
subprocess** over stdio (see `docs/ai-query-service.md`), because both
processes share the same filesystem and can see each other's `.venv`. In
Compose, `ai_service` and `product_mcp_server` are separate containers
with separate filesystems — a subprocess launch is impossible.

`product_mcp_server/app/server.py` now reads `MCP_TRANSPORT` (`stdio`
default, `http` in Docker) and switches `fastmcp`'s transport accordingly.
`ai_service/app/inventory_agent.py` reads the same variable and switches
between ADK's `StdioConnectionParams` (local subprocess) and
`StreamableHTTPConnectionParams` (networked, pointed at
`http://product_mcp_server:8100/mcp` — the Compose service name resolves
via Docker's internal DNS). No behavior differs between the two transports
from the agent's or the tools' point of view — same tool names, same
inputs/outputs, same error handling.

## Why PostgreSQL Instead of SQLite

Both `backoffice` and `product_mcp_server` need to read/write (resp.
read-only) the same stock data. Outside Docker this was a shared SQLite
file on the local filesystem; across containers, a SQLite file would need
a shared volume and is prone to locking issues under concurrent access
from two separate processes. PostgreSQL as its own `db` service sidesteps
this entirely — both containers connect over the network to one database,
which is also closer to a realistic production setup. `DATABASE_URL` /
`STOCK_DATABASE_URL` both point at
`postgresql+psycopg2://hbntory:hbntory@db:5432/hbntory` by default.

## Running

Prerequisites on the host:

```bash
ollama serve                       # or already running as a service
ollama pull qwen2.5-coder:7b       # model used by ai_service
# the Product API container/service running and reachable on :5001
```

Then, from the repo root:

```bash
docker compose up -d --build
```

This builds and starts `db`, `backoffice`, `product_mcp_server`,
`ai_service`, and `client_web`, in dependency order (`backoffice` and
`product_mcp_server` wait for `db`'s healthcheck; `ai_service` waits for
both).

Verify:

```bash
curl http://localhost:8010/login                     # Backoffice
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Give me details about product HB-LAP-1001."}'
```

Visit `http://localhost:5500/index.html` for the Client Web Interface, and
`http://localhost:8010/login` for the Backoffice (seeded admin
credentials print in `docker compose logs backoffice`).

Stop everything:

```bash
docker compose down          # keeps the Postgres volume (data persists)
docker compose down -v       # also removes the Postgres volume (fresh start)
```

## Port Conflicts

If a host port is already taken by another project's containers, edit the
`ports:` mapping for the affected service in `docker-compose.yml` (only
the **left-hand** side, the host port, needs to change — the right-hand
container port must stay as-is since other services reference it by that
number internally). This was hit and resolved during testing: `8000` and
`5432` were already bound by unrelated local containers, so `backoffice`
now maps to host port `8010` and `db` publishes no host port at all (it
only needs to be reachable from other containers on the compose network).

## Verified Behavior

All of the following were tested against the running Compose stack (stub
Product API on the host standing in for the real Docker container, which
wasn't available in this environment):

- Backoffice reachable and functional (login, admin user list) against
  PostgreSQL instead of SQLite.
- Common user created via Backoffice, logged in, added stock — persisted
  correctly in PostgreSQL (verified via `docker compose exec db psql`).
- `product_mcp_server` running in HTTP mode, reachable by `ai_service` via
  the Compose network.
- AI Query Service produced grounded, correct answers using data written
  moments earlier by the Backoffice container, through the containerized
  MCP server, confirming the full write (Backoffice → Postgres) → read
  (MCP server → Postgres, Product API → host) path works across container
  boundaries.
- Client Web Interface served by the nginx container, driven with a
  headless browser, displaying a live AI-generated answer with no console
  errors.
- The multi-branch answer-completeness limitation documented in
  `docs/ai-query-service.md` was also observed under Docker/HTTP
  transport, confirming it's a model behavior, not a transport-specific
  bug.
