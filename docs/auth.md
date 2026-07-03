# Authentication & Authorization Strategy

## Authentication mechanism: server-side session cookie

**Choice**: Starlette's `SessionMiddleware` (signed, server-verified cookie
storing only `user_id`), not JWT.

**Why**: the Backoffice is server-side rendered (see
`communication-decisions.md`) — the browser reloads a full page per action,
there's no SPA needing a portable bearer token, and no second client
(mobile app, external API consumer) that would benefit from a stateless
token. A signed session cookie is simpler to reason about here: the cookie
itself carries no user data other than an id, is signed with
`SESSION_SECRET_KEY` so it can't be forged or tampered with, and every
request re-fetches the live `User` row (so a soft-deleted or edited user is
reflected immediately, without needing token revocation logic that JWTs
would require).

**Trade-off**: doesn't scale horizontally without sticky sessions or a
shared session store — acceptable for this project's scope (single
process, single DB).

## How authentication is performed

1. `POST /login` with `username`/`password` (form-encoded).
2. `app/auth.py::authenticate_user` looks up the user by username, rejects
   if not found **or `is_active` is `False`** (soft-deleted users cannot log
   in), then verifies the password with `verify_password`.
3. On success, `log_in()` stores `user_id` in the session; the browser gets
   a signed cookie.
4. Every protected route depends on `get_current_user`, which reads
   `user_id` from the session, re-fetches the `User` row, and re-checks
   `is_active` on every request — so deactivating a user takes effect
   immediately, not just at next login.
5. `POST /logout` clears the session.

## Password storage

**Mechanism**: `bcrypt` (via the `bcrypt` package directly —
`app/security.py`), a salted, adaptive hashing algorithm purpose-built for
passwords.

- `hash_password()`: `bcrypt.hashpw(password, bcrypt.gensalt())` — generates
  a random salt per password and embeds it in the resulting hash string.
- `verify_password()`: `bcrypt.checkpw(password, stored_hash)` — recomputes
  the hash using the salt embedded in `stored_hash` and compares.
- **Why not plain SHA-256**: SHA-256 is a fast, general-purpose hash
  designed for speed (checksums, integrity) — that speed is exactly what
  makes it unsafe for passwords, since an attacker with a stolen hash
  database can brute-force billions of SHA-256 guesses per second on
  commodity GPUs. bcrypt is deliberately slow and has a tunable cost factor
  (`gensalt()` work factor), so brute-forcing scales far worse for an
  attacker. It also auto-salts every hash, preventing rainbow-table attacks
  and ensuring two users with the same password get different hashes.

(Note: `passlib[bcrypt]` was tried first but its bcrypt backend detection
is broken against recent `bcrypt` package versions — `app/security.py`
calls the `bcrypt` module directly instead, which is simpler and avoids
the dependency.)

## Role-based authorization

Two roles: `admin` and `common`, enforced via FastAPI dependencies in
`app/auth.py`, never only in templates:

- `require_admin`: 403s any non-admin. Used on all `/admin/users/*` routes.
- `require_common_user`: 403s any non-common user (i.e. blocks admin from
  stock routes). Used on all `/stock/*` routes.
- Branch scoping for common users is implicit and structural, not an extra
  check the developer could forget: every stock route reads
  `user.branch_id` from the authenticated session user and passes it to the
  service layer — there is no route parameter for "which branch," so a
  common user has no way to address another branch's stock through this
  API surface at all.
- Admin routes never touch `Stock`; common-user routes never touch `User`
  management functions — enforced by which service functions each route
  file imports, not by convention alone.

This satisfies the spec's requirement that authorization live in backend
logic: even a modified/malicious client request cannot bypass these checks,
since they run as FastAPI dependencies before the route body executes.
