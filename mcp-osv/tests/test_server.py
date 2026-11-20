import httpx
import respx

from mcp_osv.client import OSV_API
from mcp_osv.server import get_vuln_impl, mcp, query_vulns_impl
from mcp_osv.summarize import cvss3_base_score, fixed_versions, severity

RECORD = {
    "id": "GHSA-frgw-fgh6-9g52",
    "aliases": ["CVE-2014-1858"],
    "summary": "numpy writes to arbitrary files",
    "details": "Long text",
    "affected": [
        {
            "package": {"name": "numpy", "ecosystem": "PyPI"},
            "ranges": [{"events": [{"introduced": "0"}, {"fixed": "1.10.0"}, {"fixed": "1.9.2"}]}],
        }
    ],
    "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}],
    "references": [{"url": "https://example.com"}],
}


def test_summaries() -> None:
    assert cvss3_base_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") == 9.8
    assert severity(RECORD) == "critical"
    assert severity({"database_specific": {"severity": "MEDIUM"}}) == "moderate"
    assert fixed_versions(RECORD, "numpy") == ["1.9.2", "1.10.0"]


@respx.mock
async def test_query_vulns_paginates_and_sorts() -> None:
    respx.post(f"{OSV_API}/query").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "vulns": [{"id": "LOW-1", "database_specific": {"severity": "LOW"}}],
                    "next_page_token": "t",
                },
            ),
            httpx.Response(200, json={"vulns": [RECORD]}),
        ]
    )
    out = await query_vulns_impl("numpy", "1.8.1")
    assert out["count"] == 2
    assert [v["id"] for v in out["vulnerabilities"]] == ["GHSA-frgw-fgh6-9g52", "LOW-1"]


@respx.mock
async def test_errors_are_returned_not_raised() -> None:
    respx.post(f"{OSV_API}/query").mock(side_effect=httpx.ConnectError("down"))
    assert "Could not reach OSV" in (await query_vulns_impl("numpy"))["error"]
    respx.get(f"{OSV_API}/vulns/NOPE-1").respond(status_code=404)
    assert "No vulnerability" in (await get_vuln_impl("NOPE-1"))["error"]
    assert "not a valid" in (await get_vuln_impl("../etc/passwd"))["error"]


@respx.mock
async def test_get_vuln_details() -> None:
    respx.get(f"{OSV_API}/vulns/GHSA-frgw-fgh6-9g52").respond(json=RECORD)
    out = await get_vuln_impl("GHSA-frgw-fgh6-9g52")
    assert out["details"] == "Long text" and out["references"] == ["https://example.com"]


async def test_tools_are_registered() -> None:
    names = {t.name for t in await mcp.list_tools()}
    assert names == {"query_vulns", "get_vuln"}
