"""Async OSV HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

OSV_API = "https://api.osv.dev/v1"


class OSVClient:
    def __init__(self, http: httpx.AsyncClient | None = None, timeout: float = 10.0) -> None:
        self._own = http is None
        self._http = http or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._own:
            await self._http.aclose()

    async def query(
        self, package: str, version: str | None, ecosystem: str
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"package": {"name": package, "ecosystem": ecosystem}}
        if version:
            payload["version"] = version
        vulns: list[dict[str, Any]] = []
        while True:
            response = await self._http.post(f"{OSV_API}/query", json=payload)
            response.raise_for_status()
            body = response.json()
            vulns.extend(body.get("vulns") or [])
            token = body.get("next_page_token")
            if not token:
                return vulns
            payload["page_token"] = token

    async def get(self, vuln_id: str) -> dict[str, Any]:
        response = await self._http.get(f"{OSV_API}/vulns/{vuln_id}")
        response.raise_for_status()
        return response.json()
