# Database Schema — Backoffice

## 1. Scope

Stores only local system data: users, branches, and stock quantities keyed
by an external product identifier. Never stores product name, description,
price, image, or any other product metadata — that always comes live from
the Product API (see `architecture.md`).

## 2. Tables

### `branches`

| Column | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `name` | String | unique, not null |
| `created_at` | DateTime | not null, default now |

### `users`

| Column | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `username` | String | unique, not null |
| `password_hash` | String | not null |
| `role` | Enum(`admin`, `common`) | not null |
| `branch_id` | Integer | FK → `branches.id`, **nullable** |
| `is_active` | Boolean | not null, default `true` |
| `created_at` | DateTime | not null, default now |
| `updated_at` | DateTime | not null, default now, on update now |

Rules enforced by schema + app logic:

- `role = admin` → `branch_id` must be `NULL` (admin has no stock
  responsibility). Enforced at the application layer (checked on
  create/update) since a portable `CHECK` tying two columns together is
  awkward across SQLite/Postgres; documented here as the authoritative rule.
- `role = common` → `branch_id` must be `NOT NULL` (exactly one branch).
  Same enforcement point.
- Soft delete = `is_active = false`. Row is never physically removed, so
  existing `stock` rows referencing this user (if any audit trail is added
  later) and login rejection both work off this one flag.
- There is exactly one `admin` row by convention (seed script creates it;
  no UI to create another admin, per spec).

### `stock`

| Column | Type | Constraints |
|---|---|---|
| `id` | Integer | PK |
| `branch_id` | Integer | FK → `branches.id`, not null |
| `product_id` | String | not null (Product API SKU, e.g. `HB-LAP-1001` — opaque to this schema) |
| `quantity` | Integer | not null, default 0, `CHECK (quantity >= 0)` |
| `created_at` | DateTime | not null, default now |
| `updated_at` | DateTime | not null, default now, on update now |

Constraints:

- `UNIQUE (branch_id, product_id)` — one row per branch/product pair;
  add/remove stock operations update this row's `quantity` rather than
  inserting duplicates.
- `CHECK (quantity >= 0)` at the DB level as a last line of defense; the
  primary enforcement is in the application/service layer (see
  `validation-rules.md`), which validates *before* issuing the update so
  users get a clear error instead of a raw DB constraint violation.

## 3. Relationships

- `Branch 1 ── N User` (a branch has many common users; admin has none).
- `Branch 1 ── N Stock` (a branch has many stock rows).
- `Stock.product_id` is **not** a foreign key into any local table — there
  is no local `products` table. It's a plain identifier that the app uses
  to call the Product API when it needs product details.

## 4. Why No `products` Table

The spec explicitly forbids storing product names/descriptions/prices/
images/metadata locally, and a `products` table containing only an `id`
column would carry no information not already implied by `stock.product_id`
— it would exist only to "look realistic," which the spec also warns
against. If future requirements need to track *which* product ids are
known to be valid, that check goes against the live Product API, not a
local mirror.
