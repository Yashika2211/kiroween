# Architecture

```
            ┌──────────────── frontend (Next.js 14) ────────────────┐
            │ /  graveyard + summon   /jobs/[id]  certificate        │
            │ /jobs/[id]/ritual  candles · log · diffs · rise        │
            └──────────┬──────────────────────────▲──────────────────┘
               REST    │                          │ Server-Sent Events
            ┌──────────▼──────────────────────────┴──────────────────┐
            │ backend (FastAPI)                                       │
            │  api/app.py ─ jobs.py (JobManager) ─ events.py (bus)    │
            │                    │                    db.py (SQLite)  │
            │   ┌────────────────┼────────────────────────────┐       │
            │   ▼                ▼                ▼            ▼       │
            │ autopsy/        ritual/       resurrection/    rise/     │
            │  clone           planner       fixers/ (2to3,   pr_body  │
            │  markers                        pyupgrade, api, publisher│
            │  deps · pypi                    manifests,       (fork,  │
            │  osv · decay                    missing)         push,   │
            │  verdict                       smoke · llm      PR)      │
            │  service                       engine                    │
            │        └──────────── sandbox/runner.py ─────┘            │
            └──────────────────────────┬──────────────────────────────┘
                                       │ docker run (hardened, per job)
                              ┌────────▼─────────┐
                              │ python:3.12-slim │  install: network, root, caps dropped
                              │   /venv volume   │  test:    --network none, read-only,
                              └──────────────────┘           uid 1000, tmpfs
```

## Job lifecycle

`queued → autopsy → autopsied → (user presses Begin the Ritual) → ritual → resurrecting → rising → risen`

with `failed` (retryable from the ritual page) and `rejected` (too large, not Python, clone
failed). Jobs that were running when the server stopped are marked `failed: interrupted`
at startup.

Every stage publishes events (`status`, `step`, `certificate`, `plan`, `task`, `diff`, `log`,
`test`, `result`, `error`) to an in-memory bus with per-job history. The SSE endpoint replays
history from `Last-Event-ID`, then streams live, so a browser that reconnects never misses a
candle.

## Workspace

```
backend/data/workspaces/<job>/before/   pristine shallow clone (autopsy reads this)
backend/data/workspaces/<job>/after/    working copy the resurrection edits; git diff = the PR
```

## Decisions

- **Deterministic first.** 2to3, pyupgrade, the API table and manifest rewrites are
  reproducible and reviewable. Claude only sees what they couldn't fix, one file at a
  time, and its output must parse and pass the sandbox.
- **Python 2 semantics everywhere.** If any file fails to parse or the code uses
  Python-2-only builtins (`xrange`, `iteritems`, …), the whole codebase gets the full 2to3
  treatment. `map()` returning a list matters even in files that happen to parse
  (this fixed real failures in PyClojure and pyfin).
- **Static analysis never executes code.** The marker scanner blanks out strings and comments
  and uses regexes plus `ast`, so it works on files that are syntax errors in Python 3.
- **fissix, not lib2to3.** `lib2to3` was removed in Python 3.13; fissix is its maintained fork.
- **Honest results.** A resurrection whose tests still fail is "stirring", not "risen"; install
  failures that tests don't catch are reported in the PR.
- **PRs target the fork.** Opening a PR on the user's fork (not upstream) means an abandoned
  maintainer is never pinged without the user choosing to.

## mcp-osv

A standalone MCP server (`mcp-osv/`, MCP Python SDK v2) exposing `query_vulns` and
`get_vuln`. It vendors the same OSV summarising logic as `backend/necromancer/autopsy/osv.py`
so the IDE and the app agree. It is registered for Kiro in `.kiro/settings/mcp.json` and used
by the `rescan-vulns` hook.
