# Demo repositories

Three abandoned Python projects, each of which died of something different. Every feature is
checked end-to-end against these before moving on.

| Repo | Lines | Decay | Cause of death | Deterministic fixes alone | With Claude repair |
|---|---|---|---|---|---|
| [`opendoor-labs/pyfin`](https://github.com/opendoor-labs/pyfin) | 508 | 75 (Skeletal) | **Dependency rot**: pinned to numpy 1.8.1, scipy 0.14.0, wheel 0.23.0; 13 known vulnerabilities | ✅ **8/8 tests pass** | not needed |
| [`eigenhombre/PyClojure`](https://github.com/eigenhombre/PyClojure) | 574 | 54 (Decomposing) | **Acute Python 2 syndrome**: 2 files don't parse (`print` statements, `except X, e`) | installs; first 5 tests pass, then fails on `getattr(operator, "div")` | needs `ANTHROPIC_API_KEY` |
| [`nvie/times`](https://github.com/nvie/times) | 278 | 55 (Decomposing) | **Starved**: depends on the dead `unittest2`; archived | installs; first 2 tests pass, then fails on `arrow` API drift (`.timestamp` became a method) | needs `ANTHROPIC_API_KEY` |

Measured on 2026-11-20 against Docker (`python:3.12-slim`). Autopsies finish in 6–12 s; a
full deterministic resurrection takes 15–40 s per repo (dominated by `pip install`).

Tests run with `pytest -x`, so a failing run stops at the first failure: "5 passed" means the
first five passed before one failed, not that the whole suite was counted.

## What each one exercises

**pyfin**: dependency manifests (exact-pin bumps to the newest release supporting 3.12),
OSV vulnerability clearing, Python 2 semantics in code that still parses (`xrange`,
`dict.keys()` compared to a list). It also has a real pre-existing bug: `setup.py` reads
`README.rst`, which doesn't exist. Necromancer reports this in the PR instead of hiding it,
because the tests pass from source.

**PyClojure**: files that are syntax errors on Python 3 (fissix 2to3 pass), `apply()` and
`reduce()` builtins, `map()` returning a list, and a dynamic `getattr(operator, name)` that
no static tool can see. That last one is exactly what the one-file-at-a-time Claude loop is for.

**times**: dead backport package (`unittest2` → standard library), a missing test dependency
(`pytz`, added automatically after the sandbox reports `ModuleNotFoundError`), deprecated
unittest aliases, and behaviour drift in a third-party library (`arrow`).

## Reproduce

```bash
make setup
cd backend && uv run necromancer resurrect https://github.com/opendoor-labs/pyfin
```
