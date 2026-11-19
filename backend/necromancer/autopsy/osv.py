"""OSV (https://osv.dev) client: batch query, hydrate details, summarise severity and fixes.

The `mcp-osv/` server vendors the same logic so the IDE and the app agree.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Iterable
from typing import Any

import httpx
from packaging.version import InvalidVersion, Version

from necromancer.models import Severity, Vulnerability

OSV_API = "https://api.osv.dev/v1"
BATCH_LIMIT = 1000

# --------------------------------------------------------------------------- CVSS v3.x

_W = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "UI": {"N": 0.85, "R": 0.62},
    "C": {"H": 0.56, "L": 0.22, "N": 0.0},
    "I": {"H": 0.56, "L": 0.22, "N": 0.0},
    "A": {"H": 0.56, "L": 0.22, "N": 0.0},
}
_PR = {"U": {"N": 0.85, "L": 0.62, "H": 0.27}, "C": {"N": 0.85, "L": 0.68, "H": 0.5}}


def _roundup(value: float) -> float:
    as_int = round(value * 100000)
    if as_int % 10000 == 0:
        return as_int / 100000.0
    return (math.floor(as_int / 10000) + 1) / 10.0


def cvss3_base_score(vector: str) -> float | None:
    """CVSS v3.0/3.1 base score from a vector string, or None if it can't be parsed."""
    try:
        parts = dict(p.split(":", 1) for p in vector.split("/")[1:])
        scope = parts["S"]
        iss = 1 - (1 - _W["C"][parts["C"]]) * (1 - _W["I"][parts["I"]]) * (1 - _W["A"][parts["A"]])
        if scope == "U":
            impact = 6.42 * iss
        else:
            impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
        exploitability = (
            8.22
            * _W["AV"][parts["AV"]]
            * _W["AC"][parts["AC"]]
            * _PR[scope][parts["PR"]]
            * _W["UI"][parts["UI"]]
        )
    except (KeyError, ValueError):
        return None
    if impact <= 0:
        return 0.0
    if scope == "U":
        return _roundup(min(impact + exploitability, 10))
    return _roundup(min(1.08 * (impact + exploitability), 10))


def severity_from_score(score: float) -> Severity:
    if score >= 9.0:
        return Severity.CRITICAL
    if score >= 7.0:
        return Severity.HIGH
    if score >= 4.0:
        return Severity.MODERATE
    if score > 0:
        return Severity.LOW
    return Severity.UNKNOWN


def extract_severity(record: dict[str, Any]) -> Severity:
    db = (record.get("database_specific") or {}).get("severity")
    if isinstance(db, str):
        mapped = {"MEDIUM": Severity.MODERATE}.get(db.upper())
        try:
            return mapped or Severity(db.lower())
        except ValueError:
            pass
    for entry in record.get("severity") or []:
        if str(entry.get("type", "")).startswith("CVSS_V3"):
            score = cvss3_base_score(str(entry.get("score", "")))
            if score is not None:
                return severity_from_score(score)
    for affected in record.get("affected") or []:
        eco = (affected.get("ecosystem_specific") or {}).get("severity")
        if isinstance(eco, str):
            try:
                return Severity(eco.lower())
            except ValueError:
                continue
    return Severity.UNKNOWN


def extract_fixed(record: dict[str, Any], package: str, current: str | None) -> str | None:
    """Lowest fixed version for `package` that is above `current`."""
    fixes: list[Version] = []
    want = package.lower().replace("_", "-")
    for affected in record.get("affected") or []:
        name = str((affected.get("package") or {}).get("name", "")).lower().replace("_", "-")
        if name != want:
            continue
        for rng in affected.get("ranges") or []:
            for event in rng.get("events") or []:
                if "fixed" in event:
                    try:
                        fixes.append(Version(str(event["fixed"])))
                    except InvalidVersion:
                        continue
    if not fixes:
        return None
    if current:
        try:
            cur = Version(current)
            above = [v for v in fixes if v > cur]
            if above:
                return str(min(above))
        except InvalidVersion:
            pass
    return str(max(fixes))


def summarize(record: dict[str, Any], package: str, version: str | None) -> Vulnerability:
    vuln_id = str(record.get("id", ""))
    aliases = [str(a) for a in record.get("aliases") or []]
    summary = str(record.get("summary") or record.get("details") or "").strip()
    return Vulnerability(
        id=vuln_id,
        package=package,
        version=version,
        aliases=aliases,
        summary=summary.splitlines()[0][:240] if summary else "",
        severity=extract_severity(record),
        fixed=extract_fixed(record, package, version),
        url=f"https://osv.dev/vulnerability/{vuln_id}",
    )


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MODERATE: 2,
    Severity.LOW: 3,
    Severity.UNKNOWN: 4,
}

# --------------------------------------------------------------------------- client


class OSVClient:
    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 10.0) -> None:
        self._own = client is None
        self._http = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._own:
            await self._http.aclose()

    async def __aenter__(self) -> OSVClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def query_batch(
        self, packages: Iterable[tuple[str, str | None]], ecosystem: str = "PyPI"
    ) -> list[list[str]]:
        """Return vulnerability ids per (name, version) query, in order."""
        queries = []
        for name, version in packages:
            query: dict[str, Any] = {"package": {"name": name, "ecosystem": ecosystem}}
            if version:
                query["version"] = version
            queries.append(query)
        ids: list[list[str]] = []
        for start in range(0, len(queries), BATCH_LIMIT):
            chunk = queries[start : start + BATCH_LIMIT]
            response = await self._http.post(f"{OSV_API}/querybatch", json={"queries": chunk})
            response.raise_for_status()
            for result in response.json().get("results", []):
                ids.append([v["id"] for v in (result or {}).get("vulns", []) or []])
        return ids

    async def get_vuln(self, vuln_id: str) -> dict[str, Any]:
        response = await self._http.get(f"{OSV_API}/vulns/{vuln_id}")
        response.raise_for_status()
        return response.json()

    async def query(
        self, name: str, version: str | None, ecosystem: str = "PyPI"
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"package": {"name": name, "ecosystem": ecosystem}}
        if version:
            payload["version"] = version
        response = await self._http.post(f"{OSV_API}/query", json=payload)
        response.raise_for_status()
        return list(response.json().get("vulns", []) or [])


async def scan_vulnerabilities(
    packages: list[tuple[str, str]],
    *,
    client: httpx.AsyncClient | None = None,
    concurrency: int = 8,
) -> list[Vulnerability]:
    """Query OSV for pinned (name, version) pairs and return hydrated vulnerabilities,
    most severe first. Raises httpx.HTTPError on transport failure."""
    if not packages:
        return []
    async with OSVClient(client) as osv:
        id_lists = await osv.query_batch(packages)
        semaphore = asyncio.Semaphore(concurrency)
        cache: dict[str, dict[str, Any]] = {}

        async def hydrate(vuln_id: str) -> dict[str, Any]:
            if vuln_id not in cache:
                async with semaphore:
                    cache[vuln_id] = await osv.get_vuln(vuln_id)
            return cache[vuln_id]

        unique_ids = sorted({i for ids in id_lists for i in ids})
        await asyncio.gather(*(hydrate(i) for i in unique_ids))

    vulns: list[Vulnerability] = []
    for (name, version), ids in zip(packages, id_lists, strict=False):
        for vuln_id in ids:
            vulns.append(summarize(cache[vuln_id], name, version))
    vulns.sort(key=lambda v: (SEVERITY_ORDER[v.severity], v.package, v.id))
    return vulns
