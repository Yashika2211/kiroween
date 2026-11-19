# Design: Autopsy

## Pipeline
```
URL ─▶ parse_repo_url ─▶ clone (shallow, size-capped)
                              │
     ┌────────────────────────┼─────────────────────────┐
     ▼                        ▼                         ▼
GitHub metadata        static scan (ast/tokenize)   dependency parse
     │                        │                         │
     │                        │                 PyPI lookup + OSV batch
     │                        ▼                         │
     │                 install probe (sandbox)          │
     └──────────────▶ decay score + cause of death ◀────┘
                              │
                       DeathCertificate
```

GitHub metadata, PyPI lookups and OSV are fetched concurrently with `asyncio.gather`.

## Modules (`backend/necromancer/autopsy/`)
| Module        | Responsibility |
|---------------|----------------|
| `clone.py`    | `git clone --depth 50 --single-branch`, size cap, workspace path safety |
| `loc.py`      | count non-blank Python lines; enforce the 5k limit |
| `markers.py`  | Python 2 marker detection (tokenize + regex + `ast` on what parses) |
| `deps.py`     | parse requirements / setup.py (ast) / setup.cfg / pyproject |
| `pypi.py`     | latest version lookup; dead-package knowledge base |
| `osv.py`      | OSV `querybatch` + `vulns/{id}` hydration |
| `probe.py`    | install probe via `sandbox.runner` |
| `decay.py`    | decay score |
| `verdict.py`  | cause of death text |
| `service.py`  | orchestrates the above and emits progress events |

## Decay score
Each factor contributes points, capped at 100:

| Factor | Points |
|---|---|
| Years since last commit | `min(25, 5 * years)` |
| Archived | 10 |
| Files that fail to parse on 3.12 | `min(25, 50 * failing / total)` |
| Python 2 markers | `min(15, markers / 2)` |
| Vulnerabilities | `min(15, 3 * vulns)` (critical counts double) |
| Dead / missing deps | `min(10, 5 * dead)` |
| Install probe failed | 10 |

The weights are pure data in `decay.py` so the UI can show the breakdown.

## Data model
`DeathCertificate` (Pydantic) is the contract shared with the frontend
(`frontend/lib/types.ts`). It is stored as JSON in SQLite on the job row.

## Error handling
Every external call is wrapped; a failure becomes a `warnings[]` entry on the certificate rather
than failing the whole autopsy. Only URL validation, clone failure and the size limit are fatal.
