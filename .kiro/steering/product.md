---
inclusion: always
---

# Product: Necromancer

Necromancer resurrects abandoned open-source Python repositories.

A user pastes a public GitHub URL. Necromancer:

1. **Autopsy**: clones the repo and writes a Death Certificate (last commit, archived
   status, Python 2 markers, dead dependencies, OSV vulnerabilities, install/run errors,
   cause of death, decay score 0-100).
2. **Ritual**: writes a resurrection plan as a Kiro-style spec (requirements, design, tasks).
3. **Resurrection**: applies deterministic fixes first (pyupgrade-style rewrites, dependency
   bumps, known API replacements), then LLM-assisted fixes one file at a time, running tests
   in a Docker sandbox and looping until they pass.
4. **Rise**: opens a pull request on the user's fork with the autopsy and plan in the body.

## Scope rules

- Python only. Target runtime is Python 3.12.
- Repos above 5,000 lines of Python are rejected with a friendly message.
- Reliability on the three demo repos in `demo-repos.md` beats breadth.

## Users

- Maintainers who inherited a dead project.
- Engineering teams stuck on an abandoned dependency.
