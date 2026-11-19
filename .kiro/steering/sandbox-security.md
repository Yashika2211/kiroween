---
inclusion: fileMatch
fileMatchPattern: "backend/**"
---

# Sandbox security rules

Cloned repositories are untrusted code. Treat them like malware samples.

1. **Never execute cloned code on the host.** No `import`, `exec`, `subprocess` of repo
   files, `pip install` of the repo, or `setup.py` evaluation outside the Docker sandbox.
   Static analysis reads files as text and parses with `ast` only.
2. `setup.py` is parsed with `ast`, never run.
3. Sandbox containers run with:
   - `--network none` for the test phase (install phase gets network, nothing else does)
   - `--memory 1g --cpus 1 --pids-limit 256`
   - `--read-only` root filesystem plus a tmpfs `/tmp`
   - `--cap-drop ALL --security-opt no-new-privileges`
   - a non-root user
   - a hard wall-clock timeout; the container is killed and removed afterwards
4. Clone with `--depth` limits and reject repos larger than 50 MB on disk.
5. Never pass secrets (GitHub token, LLM key) into the sandbox environment.
6. Paths from the repo are resolved and checked to stay inside the workspace
   (no symlink escapes) before reading or writing.
7. LLM output is treated as untrusted text: it is applied as a file rewrite, then tested in
   the sandbox. It is never executed on the host.
