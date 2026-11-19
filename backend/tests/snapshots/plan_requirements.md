# Requirements: Resurrect someone/deadrepo

## Introduction

**Cause of death:** Acute Python 2 syndrome: 1 file fails to parse on Python 3.12 (print statement).

Decay score 78/100 (Skeletal). 120 lines of Python across 3 files.

## Requirements

### Requirement 1: Python 3.12 syntax

**User story:** As a user, I want every module to parse on Python 3.12 so that it can be imported.

#### Acceptance criteria

1. WHEN any module is parsed with Python 3.12 THEN it SHALL NOT raise SyntaxError.
2. WHEN Python 2 constructs are rewritten THEN behaviour SHALL be preserved.

### Requirement 2: Modern idioms

**User story:** As a maintainer, I want the code to use current Python idioms so it is easy to keep alive.

#### Acceptance criteria

1. WHEN the code uses removed builtins (xrange, iteritems, basestring, ...) THEN they SHALL be replaced with their Python 3 equivalents.
2. WHEN pyupgrade --py312-plus runs on the result THEN it SHALL make no further changes.

### Requirement 3: Removed standard-library modules and APIs

**User story:** As a user, I want imports and API calls to resolve on Python 3.12.

#### Acceptance criteria

1. WHEN a module imports a renamed or removed stdlib module THEN the import SHALL be rewritten to the current location.
2. WHEN a removed API has a drop-in replacement THEN it SHALL be substituted.

### Requirement 4: Installable dependencies

**User story:** As a user, I want `pip install` to succeed on Python 3.12.

#### Acceptance criteria

1. WHEN dependencies are installed on Python 3.12 THEN pip SHALL exit with status 0.
2. WHEN a dependency is dead THEN it SHALL be replaced by its successor or removed if the standard library covers it.

### Requirement 5: No known vulnerabilities

**User story:** As a security-conscious user, I want no dependency with a known advisory.

#### Acceptance criteria

1. WHEN dependencies are queried against OSV THEN no pinned version SHALL have a known vulnerability with an available fix.

### Requirement 6: Proof of life

**User story:** As a maintainer, I want automated evidence that the resurrected code works.

#### Acceptance criteria

1. WHEN the test suite runs in the sandbox THEN it SHALL pass.
2. IF the repository has no tests THEN smoke tests SHALL import every module.
3. WHERE pure functions exist THEN property tests SHALL show the resurrected function matches the original on generated inputs.
