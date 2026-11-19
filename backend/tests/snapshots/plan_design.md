# Design: Resurrect someone/deadrepo

## Approach

Deterministic fixes run first, in order, each on the output of the previous one. Every change is recorded as a unified diff. Repository code only ever runs inside the Docker sandbox (network off for tests).

```
2to3 fixers → pyupgrade → API table → manifests → smoke tests → sandbox → (LLM loop)
```

## Python 3.12 syntax (Requirement 1)

Run the 2to3 fixers (via `fissix`, a maintained lib2to3 fork) on the files that fail to parse. This is a static text transform; no repository code runs.

- constructs: print statement

Files: `deadrepo/core.py`

## Modern idioms (Requirement 2)

Run `pyupgrade --py312-plus` over every module after the syntax pass.

- 1 file use removed builtins

Files: `deadrepo/core.py`

## Removed standard-library modules and APIs (Requirement 3)

Apply Necromancer's replacement table (collections.abc, base64.encodebytes, unittest aliases, ...). Cases without a safe mechanical fix go to the LLM pass.

- issues: removed module, unittest aliases

Files: `deadrepo/core.py`, `tests/test_core.py`

## Installable dependencies (Requirement 4)

Rewrite requirement manifests in place (keeping comments and order): bump pins to the newest release that supports 3.12, swap dead packages for successors.

- `requests` 2.2.1 → 2.32.3
- `nose` is dead → pytest

Files: `requirements.txt`

## No known vulnerabilities (Requirement 5)

Raise each vulnerable pin to at least its OSV fixed version (the dependency bump usually covers this).

- GHSA-x (high) in `requests` 2.2.1 → fixed in 2.3.0

Files: `requirements.txt`

## Proof of life (Requirement 6)

Run the existing suite with pytest inside the sandbox (no network). If anything still fails, ask the LLM to repair one file at a time (max passes from config).
