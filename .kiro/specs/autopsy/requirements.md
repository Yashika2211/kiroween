# Requirements: Autopsy

## Introduction
The autopsy inspects a public GitHub Python repository and produces a Death Certificate that
explains why the project "died" and how decayed it is.

## Requirements

### Requirement 1: Accept a repository
**User story:** As a maintainer, I want to paste a GitHub URL so that Necromancer can inspect it.

#### Acceptance criteria
1. WHEN the user submits `https://github.com/<owner>/<repo>` (with or without `.git`, a trailing
   slash, or a `/tree/<branch>` suffix) THEN the system SHALL normalise it to `owner/repo`.
2. IF the URL is not a GitHub repository URL THEN the system SHALL reject it with a 422 and a
   human-readable reason.
3. IF the repository has more than 5,000 lines of Python THEN the system SHALL stop the autopsy
   and report "too large to resurrect (N lines, limit 5,000)".
4. IF the cloned repository is larger than 50 MB on disk THEN the system SHALL abort the clone.

### Requirement 2: Vital records
**User story:** As a user, I want to see when the project was born and when it died.

1. WHEN the autopsy runs THEN the system SHALL record created date, last push / last commit date,
   open issue count, stars, archived flag, default branch and licence from the GitHub API.
2. IF the GitHub API is rate-limited or unreachable THEN the system SHALL fall back to the last
   commit date from the clone and mark the API fields as unknown.

### Requirement 3: Python version markers
1. WHEN scanning `.py` files THEN the system SHALL detect Python 2 markers, including print
   statements, `except X, e`, backticks, `<>`, `ur""` literals, long integer suffixes, `exec`
   statements, octal literals like `0777`, `dict.iteritems/itervalues/iterkeys/has_key`,
   `xrange`, `raw_input`, `unicode`, `basestring`, `long`, and removed stdlib modules
   (`urllib2`, `urlparse`, `ConfigParser`, `StringIO`, `cPickle`, `Queue`, `HTMLParser`,
   `httplib`, `cookielib`, `commands`, `imp`, `asynchat`, `asyncore`, `distutils`).
2. Each marker SHALL include file, line, kind and a short excerpt.
3. The system SHALL report whether each file parses under Python 3.12 `ast`.
4. The scan SHALL never import or execute repository code.

### Requirement 4: Dependencies
1. The system SHALL parse `requirements*.txt`, `setup.py` (via `ast` only), `setup.cfg` and
   `pyproject.toml` dependency lists.
2. For each dependency the system SHALL look up the latest PyPI release and flag it as
   `outdated`, `unpinned`, `missing` (not on PyPI) or `dead` (known removed/renamed package).

### Requirement 5: Vulnerabilities
1. WHEN dependencies with a pinned or minimum version exist THEN the system SHALL query
   `https://api.osv.dev/v1/querybatch` in a single batch.
2. Each vulnerability SHALL include id, aliases (CVE), summary, severity and fixed version
   when OSV provides them.

### Requirement 6: Install probe
1. WHEN Docker is available THEN the system SHALL try to install the repo in a Python 3.12
   sandbox and record exit code and the last 60 lines of output.
2. IF Docker is unavailable THEN the probe SHALL be marked `skipped` and the certificate SHALL
   still be produced.

### Requirement 7: Verdict
1. The system SHALL compute a decay score from 0 (healthy) to 100 (fully decomposed), using
   documented weights.
2. The system SHALL write a one-sentence cause of death plus contributing factors.
3. A certificate SHALL be produced within 30 seconds for each demo repository.
