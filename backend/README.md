# Necromancer backend

FastAPI service that performs the autopsy, ritual, resurrection and rise.

```bash
uv sync
uv run uvicorn necromancer.api.app:app --reload   # http://localhost:8000/docs
uv run pytest                                      # unit + property tests (no network, no Docker)
uv run pytest -m docker                            # (opt-in) tests that need a Docker daemon
uv run necromancer resurrect https://github.com/opendoor-labs/pyfin
```

## Module map

| Package | What lives there |
|---|---|
| `necromancer/api/` | REST endpoints and the Server-Sent Events stream |
| `necromancer/jobs.py` | `JobManager`: summon → autopsy → ritual → resurrection → rise |
| `necromancer/events.py` | per-job event bus with replay (`Last-Event-ID`) |
| `necromancer/db.py` | SQLite job store |
| `necromancer/autopsy/` | `clone`, `loc`, `markers`, `deps`, `pypi`, `osv`, `decay`, `verdict`, `service` |
| `necromancer/knowledge.py` | Python 2 → 3.12 rules: syntax, builtins, removed modules, removed APIs |
| `necromancer/ritual/` | certificate → Kiro-style requirements, design, tasks |
| `necromancer/resurrection/fixers/` | `py2to3` (fissix), `modernize` (pyupgrade), `api`, `manifests`, `missing` |
| `necromancer/resurrection/smoke.py` | generated smoke tests and hypothesis property tests |
| `necromancer/resurrection/llm.py` | one-file Claude repair, with output validation |
| `necromancer/resurrection/engine.py` | runs the plan, verifies in the sandbox, loops |
| `necromancer/rise/` | PR body renderer, fork/push/PR publisher, patch fallback |
| `necromancer/sandbox/runner.py` | hardened `docker run` for install and test phases |

Configuration is read from the environment; see the root [`.env.example`](../.env.example).
