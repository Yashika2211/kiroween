# Design: mcp-osv

Built on the official `mcp` Python SDK v2 (`MCPServer`).

```
mcp_osv/
  client.py   # async OSV HTTP client (httpx): query(), get()
  summarize.py# pure helpers: severity extraction, fixed versions
  server.py   # MCPServer app registering query_vulns and get_vuln
```

The backend's autopsy uses the same `client.py` logic (vendored as `necromancer.autopsy.osv`)
so behaviour is identical between the app and the IDE.
