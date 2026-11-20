# mcp-osv

A tiny [MCP](https://modelcontextprotocol.io) server that looks up known vulnerabilities in
[OSV](https://osv.dev) for Python packages. Necromancer uses the same logic during the autopsy;
this server makes it available to Kiro (or any MCP client) while you work.

## Tools

| Tool | Arguments | Returns |
|---|---|---|
| `query_vulns` | `package`, `version` (optional), `ecosystem` (default `PyPI`) | vulnerabilities with id, CVE aliases, severity, fixed version |
| `get_vuln` | `id` (e.g. `GHSA-frgw-fgh6-9g52`, `PYSEC-2014-22`, `CVE-…`) | summary, details, severity, affected ranges, references |

## Run

```bash
uv run mcp-osv            # stdio transport
```

Kiro picks it up from `.kiro/settings/mcp.json` at the repository root.
