# MVP Definition

## Principle

The MVP covers every mandatory requirement from the spec, end to end, with
the simplest implementation of each. Nothing below is optional — this *is*
the passing bar. Anything beyond it is explicitly deferred.

## Implement First (MVP, in build order)

1. **DB schema + SQLAlchemy models**: `User` (role, branch_id nullable for
   admin, password_hash, is_active), `Branch`, `Stock` (branch_id,
   product_id, quantity, unique constraint on branch+product).
2. **Seed script**: one admin user (hashed password), two branches, sample
   stock rows.
3. **Auth**: session-based login, password hashing (bcrypt/Argon2), reject
   inactive users, protect all Backoffice routes.
4. **Authorization**: backend-enforced role checks — common user limited to
   own branch, admin blocked from stock routes and vice versa.
5. **Backoffice — common user**: add stock, remove stock (reject negative
   result), list branch stock, check product quantity.
6. **Backoffice — admin**: list/create/edit users, assign branch, change
   password, soft-delete (blocks login, keeps stock rows).
7. **Backoffice — Product API integration**: product selector/lookup by id
   in the stock screens, fetched live, never persisted.
8. **`product_mcp_server`**: `list_products`, `get_product_details` tools
   with explicit error handling (not found, API unreachable).
9. **Stock tools on the MCP server**: `get_stock_for_product`,
   `get_stock_for_branch`.
10. **`ai_service`**: one agent wired to the MCP server, REST endpoint
    `POST /query`, grounded-answer instructions (no invented data,
    explicit "unavailable" fallback), supporting the four required question
    types (product details, where is X available, what's in branch Y,
    shopping-list-across-branches).
11. **`client_web`**: single page, text input + submit + response area,
    loading state, error state, calling `ai_service` over REST.
12. **Integration pass + critical scenario tests** (all listed in task 7 of
    the spec).
13. **README** with setup/run instructions for every service.

## Leave for Later (nice-to-have, only if time allows after MVP is solid)

- Docker-composing all services together (`docker-compose.yml`) instead of
  running each with its own `venv`/instructions — valuable for the demo but
  not required for correctness.
- Automated test suite beyond the critical scenarios (e.g. full pytest
  coverage of every route).
- Nicer client UI (chat bubbles, markdown rendering of answers) beyond a
  functional page.
- Product search/autocomplete in the Backoffice beyond a basic id lookup.

## Explicitly Out of Scope (won't attempt)

- WebSocket/streaming responses (REST decision is final, see
  `communication-decisions.md`).
- Conversation history / multi-turn memory in the AI service.
- SSL/TLS (explicitly not required by the spec).
- Additional admin accounts / admin self-registration.
- A generic database MCP tool (decision made in favor of two narrow
  hand-written stock tools, see `communication-decisions.md`).
