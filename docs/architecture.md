# HBntory — Architecture Document

## 1. Overview

HBntory is an inventory management system for a fictional multi-branch retail
company. It has two user-facing surfaces:

- **Backoffice**: authenticated internal tool for admins and branch staff to
  manage users and stock.
- **Client Web Interface**: public, anonymous, natural-language product/stock
  Q&A.

The system is split into independent services so that the public-facing AI
surface cannot touch the Backoffice database directly, and so each service
can be developed, run, and reasoned about on its own.

## 2. Services and Responsibilities

| Service | Responsibility | Stack |
| --- | --- | --- |
| `backoffice/` | Authenticated web app for admin/common users. Owns the relational DB (users, branches, stock). Enforces role-based authorization. Calls the Product API for display purposes only. | FastAPI + SQLAlchemy + Jinja2 (server-side rendering) |
| `product_mcp_server/` | MCP server wrapping the external Product API. Exposes `list_products` / `get_product_details` tools (and stock-query tools, see §5). No DB access of its own to product data — it's a pass-through with error handling. | FastMCP |
| `ai_service/` | Independent backend. Hosts the AI agent(s). Receives natural-language questions from the Client Web Interface, calls MCP tools, returns grounded answers. Never talks to the Backoffice DB directly. | FastAPI + Google ADK + LiteLLM + Ollama |
| `client_web/` | Static public page (chat/search-box). No auth. Talks only to `ai_service`. | Plain HTML/CSS/JS |
| Product API | Provided externally as a Docker container ([hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api)). Read-only: list/search products, get product details by id or SKU, categories, suppliers. Not implemented by us. | Given |
| Backoffice DB | Relational database. Stores users, branches, stock rows keyed by branch + external product id. Never stores product name/description/price/image/metadata. | PostgreSQL (or SQLite for dev) |

## 3. Data Ownership — What Lives Where

- **Backoffice DB (local, ours):** users (with role, branch FK, password hash,
  active flag), branches, stock rows (`branch_id`, `product_id` [the
  Product API's SKU, e.g. `HB-LAP-1001` — chosen over its numeric `id`
  because it's what the AI agent and Backoffice UI reason about, and it's
  already the string type `stock.product_id` uses], `quantity`).
- **Product API (external, source of truth for product data):** product
  name, description, price, image, any product metadata. Never duplicated
  into our DB.
- **AI service:** stateless per request. No persistent storage of
  conversation history (not required by the project scope).

This separation is the main constraint driving the architecture: anything
that is "what is this product" goes through the Product API / MCP server;
anything that is "how many do we have, who can touch it" lives in the
Backoffice DB.

## 4. Communication Between Services

```text
                         ┌─────────────────┐
                         │   Product API    │  (external, Docker, read-only)
                         └─────────▲────────┘
                                   │ HTTP (read-only)
                    ┌──────────────┴───────────────┐
                    │                               │
           ┌────────▼─────────┐           ┌─────────▼──────────┐
           │    Backoffice      │           │ product_mcp_server  │
           │ (FastAPI + SSR)    │           │      (FastMCP)      │
           └────────┬───────────┘           └─────────▲──────────┘
                     │ SQLAlchemy                      │ MCP (stdio/HTTP)
                     │                                   │
           ┌─────────▼─────────┐             ┌───────────┴───────────┐
           │   Backoffice DB     │             │      ai_service        │
           │  (users/branches/   │◄────────────┤ (FastAPI + ADK agent)  │
           │       stock)        │  read-only  └───────────▲────────────┘
           └─────────────────────┘  stock query             │ REST
                                     (see §5)                │
                                                    ┌─────────▼──────────┐
                                                    │    client_web        │
                                                    │  (static HTML/JS)    │
                                                    └───────────────────────┘
```

- Backoffice → Product API: direct HTTP call (read-only), used only to
  render product identifiers/names in the UI. It does not persist what it
  fetches.
- Backoffice → Backoffice DB: SQLAlchemy ORM, full read/write, in-process.
- AI service → `product_mcp_server`: MCP protocol calls for product
  listing/details.
- AI service → Backoffice DB: **read-only**, for stock queries only (see §5
  for exact mechanism). Never writes.
- `client_web` → `ai_service`: REST (see decision record).

## 5. How the Agent Accesses Product and Stock Data

- **Product data**: the AI agent calls `product_mcp_server` tools
  (`list_products`, `get_product_details`), which proxy to the external
  Product API. The agent never sees or guesses product data outside of what
  the tool returns.
- **Stock data**: `product_mcp_server` is extended with two additional
  tools — `get_stock_for_product(product_id)` (quantities across all
  branches) and `get_stock_for_branch(branch_id)` — backed by a **read-only**
  SQLAlchemy session against the Backoffice DB. This keeps a single MCP
  server as the one integration point for the agent (product + stock),
  rather than introducing a second protocol (e.g. a generic DB MCP tool)
  for a schema this small. See `communication-decisions.md` for the full
  trade-off discussion.
- The agent's system instructions require it to answer only from tool
  results and to explicitly say when information is unavailable, rather
  than inventing product names, prices, or quantities.

## 6. Why Split Backoffice and AI Service

- **Blast radius**: the Client Web Interface is anonymous and public. If it
  shared a process/DB session with the Backoffice, a bug or prompt
  injection in the AI layer could reach authenticated admin functionality.
  Splitting them means the AI service physically cannot call
  user-management or stock-mutation code — it only has read-only stock
  tools and the Product MCP server.
- **Independent scaling/failure**: the Product API or the LLM backend
  (Ollama) being slow/down should not degrade Backoffice login or stock
  operations for staff.
- **Clear ownership**: Backoffice owns writes to the DB; AI service is a
  read-only consumer via MCP tools, never a second writer.
