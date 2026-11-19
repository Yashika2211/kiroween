---
inclusion: always
---

# Tech stack

| Layer     | Choice                                                         |
|-----------|----------------------------------------------------------------|
| Frontend  | Next.js 14 (App Router), TypeScript strict, Tailwind, Framer Motion |
| Backend   | Python 3.12, FastAPI, Server-Sent Events for job streams      |
| Sandbox   | One Docker container per job, network off after install       |
| Storage   | SQLite (jobs + graveyard)                                      |
| External  | GitHub REST API, OSV API, Anthropic API for code fixes         |
| MCP       | `mcp-osv/`: `query_vulns(package, version)`, `get_vuln(id)`    |

## Commands

- Backend tests: `cd backend && uv run pytest`
- Backend lint: `cd backend && uv run ruff check . && uv run ruff format --check .`
- Frontend: `cd frontend && npm run lint && npm run typecheck && npm run build`
- MCP server: `cd mcp-osv && uv run pytest`
