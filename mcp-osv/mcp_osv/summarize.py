"""Pure helpers that turn raw OSV records into compact summaries.

Kept in sync with `backend/necromancer/autopsy/osv.py` (vendored on purpose so this server
has no dependency on the backend).
"""

from __future__ import annotations

import math
from typing import Any

from packaging.version import InvalidVersion, Version

_W = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "UI": {"N": 0.85, "R": 0.62},
    "CIA": {"H": 0.56, "L": 0.22, "N": 0.0},
}
_PR = {"U": {"N": 0.85, "L": 0.62, "H": 0.27}, "C": {"N": 0.85, "L": 0.68, "H": 0.5}}


def _roundup(value: float) -> float:
    as_int = round(value * 100000)
    if as_int % 10000 == 0:
        return as_int / 100000.0
    return (math.floor(as_int / 10000) + 1) / 10.0


def cvss3_base_score(vector: str) -> float | None:
    try:
        p = dict(part.split(":", 1) for part in vector.split("/")[1:])
        scope = p["S"]
        iss = 1 - (1 - _W["CIA"][p["C"]]) * (1 - _W["CIA"][p["I"]]) * (1 - _W["CIA"][p["A"]])
        if scope == "U":
            impact = 6.42 * iss
        else:
            impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
        expl = (
            8.22 * _W["AV"][p["AV"]] * _W["AC"][p["AC"]] * _PR[scope][p["PR"]] * _W["UI"][p["UI"]]
        )
    except (KeyError, ValueError):
        return None
    if impact <= 0:
        return 0.0
    total = impact + expl if scope == "U" else 1.08 * (impact + expl)
    return _roundup(min(total, 10))


def severity(record: dict[str, Any]) -> str:
    db = (record.get("database_specific") or {}).get("severity")
    if isinstance(db, str) and db:
        return {"MEDIUM": "moderate"}.get(db.upper(), db.lower())
    for entry in record.get("severity") or []:
        if str(entry.get("type", "")).startswith("CVSS_V3"):
            score = cvss3_base_score(str(entry.get("score", "")))
            if score is not None:
                if score >= 9:
                    return "critical"
                if score >= 7:
                    return "high"
                if score >= 4:
                    return "moderate"
                return "low" if score > 0 else "unknown"
    return "unknown"


def fixed_versions(record: dict[str, Any], package: str | None = None) -> list[str]:
    found: set[str] = set()
    want = package.lower().replace("_", "-") if package else None
    for affected in record.get("affected") or []:
        name = str((affected.get("package") or {}).get("name", "")).lower().replace("_", "-")
        if want and name != want:
            continue
        for rng in affected.get("ranges") or []:
            for event in rng.get("events") or []:
                if "fixed" in event:
                    found.add(str(event["fixed"]))

    def key(v: str) -> tuple[int, Version | str]:
        try:
            return (0, Version(v))
        except InvalidVersion:
            return (1, v)

    return sorted(found, key=key)


def brief(record: dict[str, Any], package: str | None = None) -> dict[str, Any]:
    text = str(record.get("summary") or record.get("details") or "").strip()
    vid = str(record.get("id", ""))
    return {
        "id": vid,
        "aliases": list(record.get("aliases") or []),
        "summary": text.splitlines()[0][:240] if text else "",
        "severity": severity(record),
        "fixed_versions": fixed_versions(record, package),
        "url": f"https://osv.dev/vulnerability/{vid}",
    }


def detailed(record: dict[str, Any]) -> dict[str, Any]:
    out = brief(record)
    out["details"] = str(record.get("details") or "")[:4000]
    out["published"] = record.get("published")
    out["modified"] = record.get("modified")
    out["affected"] = [
        {
            "package": (a.get("package") or {}).get("name"),
            "ecosystem": (a.get("package") or {}).get("ecosystem"),
            "ranges": [r.get("events") for r in a.get("ranges") or []],
        }
        for a in record.get("affected") or []
    ]
    out["references"] = [r.get("url") for r in record.get("references") or []][:10]
    return out
