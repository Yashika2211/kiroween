---
inclusion: always
---

# Code style

## Python
- Type hints on every public function. `from __future__ import annotations` at the top.
- `ruff` is the linter and formatter (line length 100). No unused imports.
- Pure functions for analysis; side effects (network, disk, subprocess) live at the edges
  and are injected so they can be faked in tests.
- Prefer `dataclasses` / Pydantic models over loose dicts at module boundaries.
- Errors: raise a typed exception from `necromancer.errors`; never swallow exceptions silently.

## TypeScript
- `strict: true`. No `any`; use `unknown` and narrow.
- Components are function components. Client components only where interaction needs them.
- Co-locate API types in `frontend/lib/types.ts` and keep them in sync with backend schemas.

## Tests
- Every analyzer gets unit tests with small fixture repos.
- Use `hypothesis` property tests to show rewritten code behaves like the original.
- Network calls are mocked with `respx`; tests never hit the internet.

## Commits
- Conventional commits (`feat(autopsy): ...`, `fix(ui): ...`). One logical change per commit.
