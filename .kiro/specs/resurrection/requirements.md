# Requirements: Resurrection

### Requirement 1: Deterministic fixes first
1. The system SHALL apply 2to3-style fixers (via `fissix`) to files that fail to parse on 3.12.
2. The system SHALL then apply `pyupgrade --py312-plus` to every Python file.
3. The system SHALL rewrite known removed APIs (e.g. `imp` → `importlib`, `collections.Mapping`
   → `collections.abc.Mapping`, `base64.encodestring` → `encodebytes`, `inspect.getargspec`
   → `getfullargspec`, `asyncio.async` → `ensure_future`).
4. The system SHALL rewrite dependency manifests: bump outdated pins to the latest compatible
   release, replace dead packages with their successors and bump vulnerable pins to the
   lowest fixed version.

### Requirement 2: LLM-assisted fixes
1. IF tests still fail after deterministic fixes AND an LLM key is configured THEN the system
   SHALL ask the LLM to fix one file at a time, given the file and the failing output.
2. The LLM SHALL return the full new file; the system SHALL compute and store a unified diff.
3. IF the LLM output does not parse as Python 3.12 THEN it SHALL be discarded.
4. The loop SHALL run at most `NECRO_MAX_FIX_ITERATIONS` times (default 3).

### Requirement 3: Tests
1. IF the repo has no tests THEN the system SHALL generate smoke tests that import every module
   and, where possible, hypothesis property tests comparing pure functions before and after.
2. Tests SHALL run only inside the sandbox.

### Requirement 4: Visibility
1. Each applied change SHALL be streamed to the UI as a diff event with the file path.
2. The final result SHALL report which tasks passed, the number of files changed, and the test
   outcome.
