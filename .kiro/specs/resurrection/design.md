# Design: Resurrection

```
for task in plan.tasks:
    rewrite  → fixers.py2to3 (fissix) → fixers.pyupgrade → fixers.api_replacements
    deps     → fixers.requirements.rewrite_manifests()
    vulns    → bump pins to OSV fixed versions
    tests    → smoke.generate() if no tests found
    verify   → sandbox.install() + sandbox.test()
    llm      → while tests fail and i < N:
                   pick the file at the top of the failing traceback
                   llm.fix_file(path, source, failure_tail) → new source
                   reject unless ast.parse() succeeds
                   apply, diff, sandbox.test()
```

## Workspace
The original clone is copied to `workspace/<job>/after` before any change, so diffs are always
`before/` vs `after/`. Diffs use `difflib.unified_diff` with 3 lines of context.

## Fixers (`backend/necromancer/resurrection/fixers/`)
| Fixer | Engine | Notes |
|---|---|---|
| `py2to3.py` | `fissix` (maintained lib2to3 fork) | static text transform, no execution |
| `pyupgrade.py` | `pyupgrade` API | `--py312-plus` |
| `api.py` | regex + `ast` checks | table of removed APIs and their replacements |
| `requirements.py` | text rewrite | keeps comments and ordering |

## Property tests
For modules that import cleanly in both the original (if py3-parseable) and resurrected code,
`smoke.py` emits a hypothesis test per pure top-level function whose parameters have simple
annotations or default values of `int`, `str`, `float`, `bool`, `list`. The test asserts the
resurrected function returns the same value as a frozen copy of the original.

## LLM
`llm.py` calls the Anthropic Messages API. The prompt contains only the single file, the failing
test tail and the plan's guidance. No repository secrets or other files are sent.
