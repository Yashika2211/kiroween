.PHONY: setup dev api web test lint demo pull-sandbox

setup:            ## install everything
	cd backend && uv sync
	cd mcp-osv && uv sync
	cd frontend && npm ci
	docker pull python:3.12-slim

api:              ## run the API on :8000
	cd backend && uv run uvicorn necromancer.api.app:app --reload --port 8000

web:              ## run the UI on :3000
	cd frontend && npm run dev

test:             ## run every test suite
	cd backend && uv run pytest -q
	cd mcp-osv && uv run pytest -q
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd mcp-osv && uv run ruff check .
	cd frontend && npm run lint && npm run typecheck

demo:             ## resurrect the three demo repos from the CLI
	cd backend && for r in eigenhombre/PyClojure opendoor-labs/pyfin nvie/times; do \
	  uv run necromancer resurrect https://github.com/$$r || true; done
