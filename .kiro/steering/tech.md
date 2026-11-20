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
| MCP       | `mcp-osv/` (MCP Python SDK v2 `MCPServer`): `query_vulns`, `get_vuln` |
| LLM       | Anthropic Messages API, `claude-opus-5-5`, streamed, refusal fallbacks on |

## Commands

- Everything: `make setup`, `make test`, `make lint`
- Run: `make api` (port 8000) and `make web` (port 3000), or `docker compose up --build`

- Backend tests: `cd backend && uv run pytest`
- Backend lint: `cd backend && uv run ruff check . && uv run ruff format --check .`
- Frontend: `cd frontend && npm run lint && npm run typecheck && npm test && npm run build`
- MCP server: `cd mcp-osv && uv run pytest`

## Gotchas

- Docker on macOS (Colima / Docker Desktop) only shares `$HOME` with the VM. Keep workspaces under
  the repo (`backend/data/`), never `/tmp`; the sandbox refuses an empty `/src` mount.
- `lib2to3` is gone in 3.13: use `fissix`.
- Test runs use `pytest -x`, so a failing run reports only the tests before the first failure.
