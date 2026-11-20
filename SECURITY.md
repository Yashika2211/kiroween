# Security

Necromancer clones and runs code from arbitrary public repositories. The threat model and
the controls are in [`.kiro/steering/sandbox-security.md`](.kiro/steering/sandbox-security.md);
in short, repository code only ever executes inside a throwaway, capability-less Docker
container that has no network while tests run and never receives secrets.

If you deploy Necromancer publicly:

- Run the API on a dedicated VM. The API needs the Docker socket, which is root-equivalent on that host.
- Keep `NECRO_RATE_LIMIT_PER_HOUR` low and `NECRO_MAX_LINES` at 5000.
- Use a GitHub token with only the `public_repo` scope, on an account created for the purpose.

## Reporting a vulnerability

Please open a private security advisory on this repository (Security → Advisories → Report a
vulnerability) rather than a public issue. Sandbox escapes and secret leaks are the highest
priority.
