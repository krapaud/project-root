# HBntory — Inventory Management System

Multi-branch retail inventory system: an authenticated Backoffice for stock
and user management, an external read-only Product API, an MCP server
bridging product data to an AI agent, an independent AI Query Service, and a
public natural-language Client Web Interface.

## Documentation

- [Architecture](docs/architecture.md) — services, responsibilities, data
  flow, and how the AI agent accesses product/stock data.
- [Communication Decisions](docs/communication-decisions.md) — REST vs SSR,
  REST vs WebSockets, AI service ↔ MCP, AI service ↔ stock data.
- [MVP Definition](docs/mvp.md) — build order and what's explicitly deferred.

## Status

Architecture and planning phase complete (Task 0). Implementation not yet
started.
