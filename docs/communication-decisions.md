# Communication Strategy — Decision Record

## 1. Backoffice: REST + HTML/JS vs. Server-Side Rendering

**Decision: Server-Side Rendering (FastAPI + Jinja2).**

- **Benefit**: the Backoffice is a small set of CRUD-heavy screens (login,
  stock list/add/remove, user list/create/edit) gated by session auth. SSR
  lets authorization checks and rendering live in the same request/response
  cycle — no separate API surface to keep in sync with a JS frontend, no
  client-side state management, less code overall for a project of this
  size.
- **Trade-off**: less reusable if we ever wanted a mobile app or a richer
  reactive UI — a REST API + JS frontend would decouple presentation from
  logic and could serve other clients later. For this project's scope
  (internal tool, functionality over polish), that flexibility isn't worth
  the added complexity.

## 2. Client Web Interface: REST vs. WebSockets

**Decision: REST.**

- **Benefit**: each question is explicitly independent per the project spec
  (no conversation history required). A single `POST /query` request/response
  is simpler to implement, test, and debug than a WebSocket connection, and
  it matches the actual usage pattern (one question in, one answer out).
- **Trade-off**: no support for streaming tokens as the LLM generates them,
  so the user waits for the full response before seeing anything (mitigated
  with a loading indicator in the client). WebSockets would be justified if
  we wanted a live chat feel or incremental streaming — not required here.

## 3. AI Query Service ↔ MCP Tools

**Decision: the `ai_service` process holds an MCP client (via the same
library the server uses, e.g. `fastmcp.Client` or the ADK MCP toolset) and
launches/connects to `product_mcp_server` over stdio for local dev
(subprocess), with the option to switch to HTTP/SSE transport if the MCP
server needs to run as a separate container in the final deployment.**

- **Benefit**: stdio is the simplest transport for local development (no
  extra network config, no port management) and matches what was already
  validated in the `mcp-intro` project. Switching to HTTP-based MCP later
  (if `product_mcp_server` needs to run as its own Docker container
  alongside the Product API) is a transport-level change only — the tool
  definitions and agent logic don't change.
- **Trade-off**: stdio subprocess means `ai_service` and
  `product_mcp_server` must run on the same host/container, which is fine
  for this project's scale but wouldn't scale to a distributed deployment
  without switching transports.

## 4. AI Service ↔ Stock Data

**Decision: extend `product_mcp_server` with two read-only stock tools
(`get_stock_for_product`, `get_stock_for_branch`) backed directly by a
read-only SQLAlchemy session against the Backoffice DB, rather than
adopting a third-party database MCP tool (e.g. MCP Toolbox for Databases).**

- **Benefit**: the schema is small (3 tables) and the stock queries needed
  by the agent are few and well-defined (by product, by branch, "can this
  shopping list be satisfied"). A generic DB MCP tool would expose more
  surface (arbitrary queries) than needed, increasing risk for a
  public-facing agent — we'd rather hand-write two narrow, safe tools than
  give the agent broad SQL access. This also keeps a single MCP server as
  the one integration point for the agent, instead of wiring up two MCP
  servers for a project this size.
- **Trade-off**: if the schema grows significantly or more ad-hoc queries
  are needed later, a generic DB MCP tool would need less new tool code per
  new question type. For the fixed, known set of supported questions in
  this project, that flexibility isn't needed.
