# Requirements: mcp-osv

### Requirement 1: Tools
1. The server SHALL expose `query_vulns(package: str, version: str | None, ecosystem = "PyPI")`
   returning a list of vulnerabilities with id, summary, aliases, severity and fixed versions.
2. The server SHALL expose `get_vuln(id: str)` returning the full OSV record summarised.
3. Both tools SHALL return a clear error message for network failures instead of crashing.

### Requirement 2: Transport
1. The server SHALL speak MCP over stdio so Kiro and other MCP clients can launch it.
2. The server SHALL be runnable with `uv run mcp-osv`.
