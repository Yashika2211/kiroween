"""MCP server exposing `query_vulns` and `get_vuln` over stdio."""

from __future__ import annotations

import re
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

from mcp_osv.client import OSVClient
from mcp_osv.summarize import brief, detailed

mcp = MCPServer("osv")

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,80}$")
_ORDER = {"critical": 0, "high": 1, "moderate": 2, "low": 3, "unknown": 4}


async def query_vulns_impl(
    package: str,
    version: str | None = None,
    ecosystem: str = "PyPI",
    client: OSVClient | None = None,
) -> dict[str, Any]:
    osv = client or OSVClient()
    try:
        records = await osv.query(package.strip(), (version or "").strip() or None, ecosystem)
    except httpx.HTTPStatusError as exc:
        return {"error": f"OSV returned HTTP {exc.response.status_code}", "vulnerabilities": []}
    except httpx.HTTPError as exc:
        return {"error": f"Could not reach OSV: {type(exc).__name__}", "vulnerabilities": []}
    finally:
        if client is None:
            await osv.aclose()
    vulns = sorted(
        (brief(r, package) for r in records), key=lambda v: (_ORDER.get(v["severity"], 9), v["id"])
    )
    return {
        "package": package,
        "version": version,
        "ecosystem": ecosystem,
        "count": len(vulns),
        "vulnerabilities": vulns,
    }


async def get_vuln_impl(vuln_id: str, client: OSVClient | None = None) -> dict[str, Any]:
    if not _ID.match(vuln_id.strip()):
        return {"error": f"{vuln_id!r} is not a valid OSV identifier"}
    osv = client or OSVClient()
    try:
        return detailed(await osv.get(vuln_id.strip()))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return {"error": f"No vulnerability with id {vuln_id}"}
        return {"error": f"OSV returned HTTP {exc.response.status_code}"}
    except httpx.HTTPError as exc:
        return {"error": f"Could not reach OSV: {type(exc).__name__}"}
    finally:
        if client is None:
            await osv.aclose()


@mcp.tool()
async def query_vulns(
    package: str, version: str | None = None, ecosystem: str = "PyPI"
) -> dict[str, Any]:
    """List known vulnerabilities for a package (optionally at a specific version), most severe
    first, with CVE aliases and the versions that fix each one."""
    return await query_vulns_impl(package, version, ecosystem)


@mcp.tool()
async def get_vuln(id: str) -> dict[str, Any]:
    """Full details for one OSV / GHSA / PYSEC / CVE identifier."""
    return await get_vuln_impl(id)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
