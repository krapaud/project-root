# Test Evidence

## Automated Tests (Backoffice)

`backoffice/tests/` — 23 pytest tests, all passing. Run with:

```bash
cd backoffice
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

| File | Covers |
| --- | --- |
| `test_stock_service.py` | Add/remove stock, quantity never negative, rejects zero/negative quantity, rejects unknown product (mocked Product API), rejects invalid branch, per-branch isolation. |
| `test_user_service.py` | Admin creates common user, rejects duplicate username, soft-delete flips `is_active` without deleting the row, admin cannot be soft-deleted through user management, password change updates the hash. |
| `test_auth.py` | Correct/incorrect credentials, unknown username, **soft-deleted user cannot authenticate**. |
| `test_authorization_routes.py` | Full HTTP route level via `TestClient`: admin blocked (403) from `/stock/*`, common user blocked (403) from `/admin/users/*`, anonymous request redirected/rejected, common user can add stock to their own branch, deleted user's login attempt returns "Invalid username or password". |

Result at last run:

```text
======================== 23 passed, 1 warning in 4.51s =========================
```

(The one warning is `starlette.testclient`'s httpx deprecation notice, unrelated to test correctness.)

## Critical Scenarios — Mapping to Tests/Evidence

Per Task 7's required scenario list:

| # | Scenario | Verified by |
| --- | --- | --- |
| 1 | Common user adds valid stock | `test_common_user_adds_valid_stock`, integration run step 7 |
| 2 | Common user removes valid stock | `test_common_user_removes_valid_stock` |
| 3 | Common user cannot remove more stock than available | `test_common_user_cannot_remove_more_stock_than_available`, `test_stock_quantity_never_goes_negative` |
| 4 | Common user cannot operate on another branch | Structural: stock routes always use `user.branch_id` from the session, no branch parameter exists on the route (`docs/auth.md`) — no route path allows addressing another branch at all |
| 5 | Admin can create a common user | `test_admin_can_create_common_user`, integration run step 5 |
| 6 | Admin can soft-delete a user | `test_admin_can_soft_delete_user`, `test_soft_delete_does_not_remove_user_row` |
| 7 | Deleted user cannot log in | `test_deleted_user_cannot_authenticate`, `test_deleted_user_login_rejected` (HTTP level) |
| 8 | Admin cannot manage stock | `test_admin_cannot_access_stock_routes` |
| 9 | Product details obtained from external API | `test_common_user_can_add_stock_to_own_branch` (mocked API call asserted), integration run step 9 (real stub API), verified stock table has no product metadata columns (integration step 8) |
| 10 | AI can answer where a product is available | Manual test, `docs/ai-query-service.md` and integration run — Downtown (40)/Airport (5) reflected correctly after a live stock change |
| 11 | AI can answer what products are available in a branch | Manual test, integration run (browser-driven, Playwright) |
| 12 | AI gives a clear response for unknown products | `docs/ai-query-service.md`: "There is no product with the identifier 'does-not-exist'..." |
| 13 | AI gives a clear response when information is unavailable | Integration run: asked "What is the weather today?" → agent explicitly declined, restating its actual scope, rather than inventing an answer |

## Full-System Integration Run

Executed once, in order, with a stub Product API (not the real Docker
container, which wasn't available in this environment) and every other
service exactly as it will run in the final system:

1. Product API (stub) started and responding.
2. Backoffice DB initialized via `scripts/seed.py` (admin + 2 branches + sample stock).
3. Backoffice service started; `/login` reachable.
4. Admin authenticates (`HTTP 303` redirect on success).
5. Admin creates common user `bob` on branch 1 — confirmed in the rendered user list.
6. `bob` authenticates as a common user.
7. `bob` adds 15 units of `prod-001` to his branch — confirmed in the rendered stock table.
8. Verified via direct SQLite inspection that the `stock` table's columns
   are exactly `id, branch_id, product_id, quantity, created_at,
   updated_at` — no product name/price/description ever touches this
   table.
9. Product MCP Server's `get_product_details` tool returns live data from
   the stub Product API for `prod-001`.
10. Product MCP Server's `get_stock_for_branch` tool reflects the same DB
    that step 7 wrote to (**40** units — 25 seeded + 15 added), proving the
    Backoffice write and the MCP read-only stock tool share one source of
    truth in real time.
11. AI Query Service (`qwen2.5-coder:7b` via Ollama) answers "Which branch
    has stock of prod-001?" with the updated 40/5 split — correct and
    current.
12. Client Web Interface served as a static page.
13. Page driven with a headless browser (Playwright): typed a question,
    submitted, and the DOM rendered the AI service's live answer with no
    console errors.

This confirms every service boundary in `docs/architecture.md`'s diagram
was exercised with real data flowing end-to-end, not just unit-tested in
isolation.

**Note**: the 13-step run above used an early, simplified stub (ids like
`prod-001`) predating confirmation of the real Product API's contract. The
integration was re-run after the client/tool code was updated to the real
contract (SKU-based ids, `/api/v1/products/{id_or_sku}` path, structured
`{"error": "not_found", ...}` 404 body) — see "Product Data" below.

## Product Data — Real API Contract

[hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api)
is the actual Product API to be run via Docker. Its contract differs from
early assumptions in two ways that required code changes (both applied and
re-tested):

- Path is `GET /api/v1/products/{id_or_sku}`, not `GET /products/{id}`.
- The product identifier used throughout HBntory is the API's **SKU**
  field (e.g. `HB-LAP-1001`), not its separate numeric `id`.
- 404 responses have a structured body (`{"error": "not_found", "message":
  "Product not found."}`) rather than an empty one — handled identically
  by `ProductNotFoundError` either way, since only the status code is
  checked.

Re-verified against a stub matching this real contract:

- `product_mcp_server`'s `get_product_details('HB-LAP-1001')` returned the
  full real-shaped product (`sku`, `unit_price`, `currency`, `tags`, etc.).
- `product_mcp_server`'s `get_stock_for_product('HB-LAP-1001')` correctly
  joined this SKU against Backoffice stock rows seeded with the same SKU.
- The Backoffice stock-add flow correctly validated `HB-LAP-1001` as an
  existing product and rejected `NOT-A-REAL-SKU` with a clear error derived
  from the real 404 body.
- The AI Query Service produced a grounded, correctly-formatted answer for
  "Give me details about product HB-LAP-1001," using the real API's richer
  field set — see `docs/ai-query-service.md`.

## Known Gap

The real Product API Docker container was not run in this environment
(Docker wasn't available) — only its documented contract was; all testing
used a FastAPI stub reproducing that exact contract (paths, field names,
404 shape). Pointing `PRODUCT_API_BASE_URL` at the real container (default
`http://localhost:5001` per its README) should require no further code
changes, since the Backoffice, MCP server, and AI service only depend on
the HTTP contract, which the stub now matches exactly.
