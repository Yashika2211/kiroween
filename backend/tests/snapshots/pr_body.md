## 🪦 Death Certificate

**someone/deadrepo** (2011 – 2013)

> **Cause of death:** Acute Python 2 syndrome: 1 file fails to parse on Python 3.12 (print statement).

**Decay score:** 78/100 (Skeletal)

| Finding | Count |
|---|---|
| Python files | 3 (120 lines) |
| Files that fail to parse on 3.12 | 1 |
| Legacy markers | 4 |
| Outdated dependencies | 1 |
| Dead dependencies | 1 |
| Known vulnerabilities | 1 |

## 🕯️ The Ritual

- [x] Rewrite Python 2 syntax with 2to3 fixers
- [x] Modernise idioms with pyupgrade --py312-plus
- [x] Replace removed stdlib modules and APIs
- [x] Bump and replace dependencies
- [x] Raise vulnerable pins to fixed versions
- [x] Add smoke tests and property tests
- [x] Install on Python 3.12 and run tests in the sandbox
- [ ] Repair remaining failures with the LLM, one file at a time (skipped: tests already pass)

## 🧟 Resurrection

✅ Tests pass on Python 3.12 in an isolated sandbox: `5 passed in 0.3s`

**2 files changed.** Changes by source:

- 2to3 fixers (fissix): 1
- pyupgrade --py312-plus: 1
- dependency manifests: 1

Generated tests:

- `tests/test_necromancer_smoke.py`

<details><summary>Dependency changes</summary>

- nose: nose is dead; replaced by pytest

</details>

<details><summary>Vulnerabilities addressed</summary>

- [GHSA-x]() high in `requests` 2.2.1 → fixed in 2.3.0

</details>

The full resurrection spec (requirements, design, tasks) is in `.necromancer/plan/`.

---
_Raised from the dead by [Necromancer](https://github.com/Yashika2211/kiroween). Repository code only ran inside a network-isolated Docker sandbox. Please review before merging._
