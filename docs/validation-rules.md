# Stock Validation Rules — Where and Why

## Where validation lives

All stock business rules are enforced in `backoffice/app/services/stock_service.py`,
**not** in the route handlers and not relied upon at the database layer alone.
The DB still carries a `CHECK (quantity >= 0)` and a
`UNIQUE (branch_id, product_id)` constraint (see `database-schema.md`) as a
last line of defense, but the service layer is what turns an invalid
operation into a clear `StockValidationError` before any SQL runs — so users
see "only 3 available" instead of a raw constraint violation.

**Why the service layer and not the route handler**: routes will exist for
both the Backoffice UI and (potentially) any future API surface; putting the
rules in one shared function means every caller gets the same guarantees
without duplicating checks per route.

## Rules and enforcement points

| Rule | Enforced by | Detail |
|---|---|---|
| Stock quantity cannot become negative | `remove_stock()` (pre-check) + DB `CHECK` (backstop) | Remove is rejected up front if `requested > available`; the DB constraint would only fire if a bug bypassed the service layer. |
| Stock changes require positive integer quantities | `_validate_quantity()` | Rejects zero, negative, non-integer, and `bool` (since `bool` is a subclass of `int` in Python and would otherwise silently pass an `isinstance(x, int)` check). |
| Stock operations reference valid branches | `_get_branch_or_raise()` | Looks up the branch by id before touching `Stock`; raises if it doesn't exist. |
| Stock operations reference product identifiers that exist in the external Product API | `_validate_product_exists()` | Calls `product_api_client.get_product()`; a `404`-equivalent raises `StockValidationError` with a clear "no product found" message; a connection/API failure raises a distinct, clear error rather than silently allowing the operation. |

## Add vs. Remove semantics

- `add_stock`: creates the `Stock` row (quantity `0`) if this is the first
  time this branch/product pair is stocked, then increments. This keeps the
  `UNIQUE (branch_id, product_id)` constraint meaningful — one row per pair,
  ever.
- `remove_stock`: never creates a row; removing from a branch/product with
  no existing stock (or insufficient quantity) is rejected with the actual
  available amount in the error message.

## Authorization vs. validation

Validation rules above only decide *whether an operation is well-formed*.
*Whether the calling user is allowed to perform it at all* (branch
ownership, admin vs. common role) is a separate authorization concern,
enforced in the route/dependency layer per `communication-decisions.md`
and Task 2 (Backoffice Authentication and Authorization) — kept distinct so
each concern is testable on its own.
