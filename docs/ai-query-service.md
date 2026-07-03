# AI Query Service

## Overview

`ai_service/` is an independent FastAPI backend hosting a single Google ADK
agent (`inventory_assistant`). It receives natural-language questions from
`client_web/` over REST and answers them using only data obtained through
`product_mcp_server`'s tools — never invented.

## Supported Question Types

1. **Product details** — "Give me details about product X."
2. **Where a product is available** — "Which branch has stock of product X?"
3. **What's in a branch** — "What products can I find in branch Y?"
4. **Shopping-list recommendation** — "If I want to buy N units of X, M
   units of Y, ..., which branch or branches should I visit?"

Anything outside this scope, or a tool call that returns an error or no
data, is answered with an explicit "unavailable"/"not found" statement per
the agent's system instruction (`app/inventory_agent.py::INSTRUCTION`) —
never a guess.

## Agent → MCP Connection

The agent uses ADK's `McpToolset` with `StdioConnectionParams`, launching
`product_mcp_server` as a subprocess (`python3 -m app.server`) per the
transport decision in `communication-decisions.md` §3. Two details worth
noting for anyone re-running this:

- The subprocess must run with **`product_mcp_server`'s own Python
  interpreter** (its `.venv`), not `ai_service`'s — they have different
  dependencies (`fastmcp` lives only in the MCP server's venv). This is
  configurable via the `MCP_SERVER_PYTHON` env var if the default path
  (`product_mcp_server/.venv/bin/python3`) doesn't apply.
- `PRODUCT_API_BASE_URL` and `STOCK_DATABASE_URL` are passed through as
  environment variables to the subprocess, so the MCP server picks up the
  same configuration as the rest of the system.

Tool calls are observable: ADK/LiteLLM logs each tool invocation and its
arguments to stdout, which is how a validation-error retry (see below) was
caught during testing.

## Model

**`qwen2.5-coder:7b`** (via Ollama). Three models were tried:

- `llama3.2:1b` — produced malformed/hallucinated output when asked to use
  tools (e.g. echoing an internal request-format artifact instead of
  calling `get_product_details`), consistent with the tool-use limitations
  already noted in `ai-agents-intro`/`capstone-agentic` for very small
  models.
- `qwen2.5-coder:14b` — reliably failed to produce any usable answer at
  all (returned empty/malformed JSON, e.g. `` ```json\n\n``` ``), likely a
  tool-call formatting incompatibility between this model and
  LiteLLM/Ollama's function-calling path. Not investigated further since
  `7b` already worked adequately.
- `qwen2.5-coder:7b` — chosen as the default. Usually reliable for the
  three single-lookup question types (product details, branch
  availability, branch contents), but not perfectly: see the note on
  multi-branch results below.

### Known limitation: incomplete multi-branch results

Even for a single-product "which branch has stock" question, when a
product exists in more than one branch the model occasionally reports
only one branch instead of all of them — observed both with the stdio
transport (local dev) and the HTTP transport (Docker Compose), so it is
not transport-related. Repeating an identical question against unchanged
data can yield a complete, correct answer on one call and an incomplete
one (missing a branch) on the next. The underlying `get_stock_for_product`
tool itself was directly verified (via SQL against the Postgres container)
to consistently return all branches correctly — the loss happens when the
model synthesizes the tool result into text, not in the data or the MCP
server.

### Known limitation: multi-product shopping-list questions

Question type 4 (shopping-list recommendation across multiple products)
requires the agent to call `get_stock_for_product` more than once in a
single turn and reason over the combined results. With `qwen2.5-coder:7b`
this is **not reliable** — repeating the identical question yields
different outcomes across runs:

- Sometimes correct and grounded.
- Sometimes the raw MCP `<tool_response>` JSON leaks directly into the
  answer instead of being synthesized into text.
- Sometimes the quantity attributed to a branch is fabricated/inconsistent
  with what the tool actually returned (verified by calling the same tool
  directly and comparing).

Each individual tool call was independently verified to return correct,
stable data (see "Manually Verified Behavior" below and
`docs/mcp-server.md`) — the instability is in the model's handling of
multiple sequential tool calls within one turn, not in the MCP server or
the stock data. The system instruction
(`app/inventory_agent.py::INSTRUCTION`) was tightened to spell out an
explicit step-by-step procedure for this question type, which helped but
did not fully resolve the inconsistency. Question types 1–3 (single tool
call each) were not observed to have this problem.

**If this needs to be fixed for a demo**: the most reliable option would
be to special-case shopping-list questions with deterministic Python logic
(call the stock tools directly, compare against requested quantities, and
only use the LLM to phrase the final sentence) rather than trusting the
model to orchestrate multiple tool calls unsupervised. This was not
implemented, to keep the agent's logic uniform across all four question
types, and because it wasn't required for this project's scope.

## Manually Verified Behavior

**Note**: the runs below predate confirmation of the real Product API's
contract ([hbtn-edu/hbntory-products-api](https://github.com/hbtn-edu/hbntory-products-api))
and use placeholder ids (`prod-001` etc.) from an earlier, simplified stub.
The same question types were re-verified after switching to the real
contract (`GET /api/v1/products/{id_or_sku}`, SKU-based ids like
`HB-LAP-1001`) — see `docs/test-evidence.md`'s integration run and the
"Product Data" section below for that confirmation. Both runs exercise the
identical agent/tool code path; only the underlying product ids/schema
differ.

With a stub Product API (`prod-001`/`prod-002`/`prod-003`) and the seeded
Backoffice DB (branches Downtown/Airport):

| Question | Result |
| --- | --- |
| "Give me details about product prod-001." | Correct name/price from the stub API. |
| "Which branch has stock of product prod-001?" | Correctly listed both Downtown (25) and Airport (5). |
| "What products can I find in branch 1?" | Correctly listed prod-001 (25) and prod-002 (10). |
| "Give me details about product does-not-exist." | Explicit "no product with that identifier" — no invention. |
| "Buy 10 of prod-001 and 5 of prod-002 — which branch(es)?" | Correctly identified Airport as the only branch holding both; one intermediate tool call had invalid arguments (passed a list instead of a string) and was retried by the agent before answering correctly. |
| Empty question via `POST /query` | Short-circuited before reaching the agent: "Please ask a question about products or stock." |

### Re-verified against the real API's contract

```text
Q: Give me details about product HB-LAP-1001.
A: Holberton Student Laptop 14 — a training catalog item for HBntory
   integration, categorized under Laptops, supplied by Holberton Tools Co.,
   priced at USD 799, weighing 1.35 kg, tagged student/portable/linux-ready.
```

Confirms the agent correctly consumes the real API's richer product schema
(`sku`, `unit_price`, `currency`, `tags`, etc.) through the same
`get_product_details` tool, with no code changes beyond the client/tool
pointing at the real path and field names.

## Endpoint

```text
POST /query
{"question": "..."}
→ {"answer": "..."}
```

Each request is independent (`InMemoryRunner` creates a fresh session per
call) — no conversation history is stored, per the project's scope and the
REST decision in `communication-decisions.md` §2.

## Running

```bash
cd ai_service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # adjust MODEL_NAME / API URLs

# Ollama must be running with the model pulled:
ollama pull qwen2.5-coder:7b

uvicorn app.main:app --port 9000
```

Requires `product_mcp_server` to have its own `.venv` set up (its
dependencies are installed separately — see `docs/mcp-server.md`), since
`ai_service` launches it as a subprocess rather than importing it.
