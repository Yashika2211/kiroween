import pytest
import respx

from necromancer.autopsy.osv import (
    OSV_API,
    cvss3_base_score,
    extract_fixed,
    extract_severity,
    scan_vulnerabilities,
    summarize,
)
from necromancer.models import Severity

NUMPY_VULN = {
    "id": "GHSA-frgw-fgh6-9g52",
    "aliases": ["CVE-2014-1858"],
    "summary": "numpy allows local users to write to arbitrary files",
    "affected": [
        {
            "package": {"name": "numpy", "ecosystem": "PyPI"},
            "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "1.10.0"}]}],
        }
    ],
    "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N"}],
}


@pytest.mark.parametrize(
    ("vector", "expected"),
    [
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", 10.0),
        ("CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N", 5.5),
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", 6.1),
        ("CVSS:3.0/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:N", 0.0),
    ],
)
def test_cvss3_known_scores(vector: str, expected: float) -> None:
    assert cvss3_base_score(vector) == expected


def test_cvss3_garbage() -> None:
    assert cvss3_base_score("not a vector") is None
    assert cvss3_base_score("CVSS:3.1/AV:X") is None


def test_severity_prefers_database_specific() -> None:
    assert extract_severity({"database_specific": {"severity": "MEDIUM"}}) is Severity.MODERATE
    assert extract_severity({"database_specific": {"severity": "CRITICAL"}}) is Severity.CRITICAL
    assert extract_severity(NUMPY_VULN) is Severity.MODERATE
    assert extract_severity({}) is Severity.UNKNOWN


def test_fixed_version_is_lowest_above_current() -> None:
    record = {
        "affected": [
            {
                "package": {"name": "Django"},
                "ranges": [
                    {"events": [{"introduced": "0"}, {"fixed": "1.4.18"}]},
                    {"events": [{"introduced": "1.6"}, {"fixed": "1.6.10"}]},
                    {"events": [{"introduced": "1.7"}, {"fixed": "1.7.3"}]},
                ],
            }
        ]
    }
    assert extract_fixed(record, "django", "1.6.2") == "1.6.10"
    assert extract_fixed(record, "django", "9.0") == "1.7.3"
    assert extract_fixed(record, "flask", "1.0") is None


def test_summarize() -> None:
    v = summarize(NUMPY_VULN, "numpy", "1.8.1")
    assert v.fixed == "1.10.0"
    assert v.aliases == ["CVE-2014-1858"]
    assert v.url.endswith("GHSA-frgw-fgh6-9g52")


@respx.mock
async def test_scan_vulnerabilities_batches_and_hydrates_once() -> None:
    batch = respx.post(f"{OSV_API}/querybatch").respond(
        json={
            "results": [
                {"vulns": [{"id": "GHSA-frgw-fgh6-9g52"}]},
                {},
                {"vulns": [{"id": "GHSA-frgw-fgh6-9g52"}, {"id": "PYSEC-1"}]},
            ]
        }
    )
    detail = respx.get(f"{OSV_API}/vulns/GHSA-frgw-fgh6-9g52").respond(json=NUMPY_VULN)
    respx.get(f"{OSV_API}/vulns/PYSEC-1").respond(
        json={"id": "PYSEC-1", "database_specific": {"severity": "CRITICAL"}}
    )
    vulns = await scan_vulnerabilities([("numpy", "1.8.1"), ("six", "1.9.0"), ("numpy", "1.7.0")])
    assert batch.call_count == 1
    assert detail.call_count == 1
    assert vulns[0].id == "PYSEC-1"
    assert len(vulns) == 3


async def test_scan_with_no_packages_skips_network() -> None:
    assert await scan_vulnerabilities([]) == []
