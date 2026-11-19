# Requirements: Sandbox

## Introduction
All repository code runs inside a disposable Docker container. The host never imports or
executes cloned code.

### Requirement 1: Isolation
1. The sandbox SHALL run each command in a fresh container from `python:3.12-slim`.
2. The container SHALL run as a non-root user with all capabilities dropped,
   `no-new-privileges`, a read-only root filesystem and a writable tmpfs at `/tmp`.
3. The container SHALL be limited to 1 CPU, 1 GiB memory and 256 processes.
4. The test phase SHALL run with `--network none`.
5. Secrets from the host environment SHALL NOT be passed into the container.

### Requirement 2: Two-phase execution
1. WHEN the install phase runs THEN the system SHALL install dependencies into a per-job
   volume-backed virtualenv with network access.
2. WHEN the test phase runs THEN the system SHALL mount the repo and the virtualenv read-only
   (repo writable copy for test caches) and run with no network.

### Requirement 3: Limits and cleanup
1. Each phase SHALL have a wall-clock timeout (install 180 s, tests 120 s by default).
2. IF the timeout expires THEN the container SHALL be killed and the result marked `timeout`.
3. Containers and volumes SHALL be removed after the job, success or failure.

### Requirement 4: Results
1. Each run SHALL return exit code, status (`passed`, `failed`, `timeout`, `error`, `skipped`),
   duration, and a bounded tail of combined output (60 lines, 16 KB).
2. IF Docker is not available THEN runs SHALL return `skipped` with a reason.
