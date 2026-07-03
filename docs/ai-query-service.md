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

**`qwen2.5-coder:7b`** (via Ollama), not `llama3.2:1b`. Both were tried;
`llama3.2:1b` produced malformed/hallucinated output when asked to use
tools (e.g. echoing an internal request-format artifact instead of calling
`get_product_details`), consistent with the tool-use limitations already
noted in `ai-agents-intro`/`capstone-agentic` for very small models.
`qwen2.5-coder:7b` reliably called tools and produced grounded answers
across all four supported question types.

## Manually Verified Behavior

With a stub Product API (`prod-001`/`prod-002`/`prod-003`) and the seeded
Backoffice DB (branches Downtown/Airport):

| Question | Result |
|---|---|
| "Give me details about product prod-001." | Correct name/price from the stub API. |
| "Which branch has stock of product prod-001?" | Correctly listed both Downtown (25) and Airport (5). |
| "What products can I find in branch 1?" | Correctly listed prod-001 (25) and prod-002 (10). |
| "Give me details about product does-not-exist." | Explicit "no product with that identifier" — no invention. |
| "Buy 10 of prod-001 and 5 of prod-002 — which branch(es)?" | Correctly identified Airport as the only branch holding both; one intermediate tool call had invalid arguments (passed a list instead of a string) and was retried by the agent before answering correctly. |
| Empty question via `POST /query` | Short-circuited before reaching the agent: "Please ask a question about products or stock." |

## Endpoint

```
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
