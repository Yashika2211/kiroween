# Requirements: Rise (pull request)

### Requirement 1: Fork and branch
1. WHEN resurrection finishes and a GitHub token is configured THEN the system SHALL fork the
   repository to the token owner's account (reusing an existing fork).
2. The system SHALL push the changes to a new branch `necromancer/resurrect-<short-job-id>`.
3. The token SHALL be passed to git through an environment-scoped credential helper, never
   written to disk or into a remote URL that is logged.

### Requirement 2: Pull request
1. The system SHALL open a pull request from the new branch against the fork's default branch.
2. The PR body SHALL include the cause of death, the decay score, a findings table, the task
   checklist with outcomes and the test result.
3. The PR URL SHALL be stored on the job and shown in the UI.

### Requirement 3: Without a token
1. IF no token is configured THEN the system SHALL produce a downloadable `.patch` file and the
   PR body markdown instead of failing.
