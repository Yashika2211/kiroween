# Requirements: Ritual (resurrection plan)

## Introduction
The ritual turns a Death Certificate into a Kiro-style spec for bringing the repo back:
`requirements.md`, `design.md` and `tasks.md`.

### Requirement 1: Plan generation
1. WHEN a certificate is complete THEN the system SHALL generate a plan deterministically from
   its findings, without needing an LLM.
2. The requirements document SHALL contain one requirement per problem class found
   (syntax, stdlib moves, dependencies, vulnerabilities, tests) using EARS acceptance criteria.
3. The design document SHALL list the fix strategy for each class (deterministic rewriter,
   dependency bump, LLM-assisted) and the files affected.
4. The tasks document SHALL be an ordered checklist where each task references the requirement
   it satisfies and the files it touches.

### Requirement 2: Ordering
1. Tasks SHALL be ordered: syntax rewrites, stdlib/API replacements, dependency bumps,
   vulnerability fixes, LLM fixes for remaining failures, smoke tests, final test run.
2. IF a problem class has no findings THEN its tasks SHALL be omitted.

### Requirement 3: Output
1. The plan SHALL be stored on the job and returned by the API as markdown strings.
2. The plan SHALL be written into the resurrected repo under `.necromancer/plan/` and summarised
   in the pull request body.
