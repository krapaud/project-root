# Product MCP Server

## Overview

`product_mcp_server/app/server.py` is a [FastMCP](https://gofastmcp.com)
server bridging the AI agent to two data sources:

- The external **Product API** (read-only, Docker container) — product
  listing and details.
- The **Backoffice database** (read-only connection) — stock quantities,
  per the architectural decision in `communication-decisions.md` §4 to
  extend this same MCP server rather than adopt a generic database MCP
  tool.

## Tools Exposed

| Tool | Input | Output | Notes |
|---|---|---|---|
| `list_products` | none | `list[dict]` of products, or `[{"error": ...}]` | Proxies `GET /products` on the Product API. |
| `get_product_details` | `product_id: str` | product `dict`, or `{"error": ...}` | Proxies `GET /products/{id}`. Distinguishes "not found" from "API unreachable" in the error message. |
| `get_stock_for_product` | `product_id: str` | `{"product_id", "branches": [{"branch_id", "branch_name", "quantity"}]}` | Read-only SQL join against `stock`/`branches`. Empty list (not an error) if the product has no stock anywhere. |
| `get_stock_for_branch` | `branch_id: int` | `{"branch_id", "products": [{"product_id", "quantity"}]}` | Read-only SQL against `stock`. Empty list if the branch has no stock rows. |

Only these four capabilities are exposed — no write access, no arbitrary
query passthrough — to keep the surface an autonomous agent can reach as
small and predictable as possible (same principle documented for
third-party MCP servers in the `mcp-intro` project review).

## Error Handling

The server never fails silently — every tool returns a structured
`{"error": "..."}` payload the agent can read and relay, instead of raising
an unhandled exception or returning empty/null data that could be mistaken
for "no results":

- **Product not found**: `get_product_details` on an unknown id returns
  `{"error": "No product found with id '<id>'"}` (HTTP 404 from the Product
  API mapped to `ProductNotFoundError`).
- **Product API unreachable**: connection errors (`httpx.RequestError`) or
  non-2xx/404 responses are mapped to `ProductAPIError` and surfaced as
  `{"error": "Could not reach Product API: ..."}`.
- **Stock database unreachable**: any exception from the SQL query is
  caught and surfaced as `{"error": "Could not query stock database: ..."}`
  via `StockQueryError`.
- **No stock recorded** (product with zero stock rows, or empty branch) is
  explicitly **not** treated as an error — it returns an empty list plus a
  `"note"` field, since "no data" and "lookup failed" are different
  situations the agent (and end user) need to distinguish.

## Manual Testing

`product_mcp_server/test_client.py` connects an in-process `fastmcp.Client`
to the server and exercises all four tools, including the two "expected
failure" paths (unknown product id, branch with no stock). Verified runs:

```
Available tools: ['list_products', 'get_product_details', 'get_stock_for_product', 'get_stock_for_branch']

--- list_products() ---
[{'id': 'prod-001', 'name': 'Widget', 'price': 9.99}]

--- get_product_details('prod-001') [valid] ---
{'id': 'prod-001', 'name': 'Widget', 'price': 9.99}

--- get_product_details('does-not-exist') [invalid id] ---
{'error': "No product found with id 'does-not-exist'"}

--- get_stock_for_product('prod-001') ---
{'product_id': 'prod-001', 'branches': [{'branch_id': 1, 'branch_name': 'Downtown', 'quantity': 25}, {'branch_id': 2, 'branch_name': 'Airport', 'quantity': 5}]}

--- get_stock_for_branch(1) ---
{'branch_id': 1, 'products': [{'product_id': 'prod-001', 'quantity': 25}, {'product_id': 'prod-002', 'quantity': 10}]}

--- get_stock_for_branch(999) [no stock] ---
{'branch_id': 999, 'products': [], 'note': 'No stock recorded for this branch.'}
```

Separately verified: stopping the Product API and re-calling
`get_product_details` returns
`{'error': 'Could not reach Product API: [Errno 61] Connection refused'}`
rather than hanging or raising an unhandled exception.

## Running

```bash
cd product_mcp_server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # adjust PRODUCT_API_BASE_URL / STOCK_DATABASE_URL

python3 test_client.py       # manual test run
python3 -m app.server         # run standalone over stdio (normally launched by ai_service instead)
```
