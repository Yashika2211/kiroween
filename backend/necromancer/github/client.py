"""Thin async GitHub REST client covering only what Necromancer needs."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx

from necromancer.github.urls import RepoRef
from necromancer.models import VitalRecords

API = "https://api.github.com"


class GitHubError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"GitHub API {status}: {message}")
        self.status = status


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "necromancer-resurrector",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._token = token
        self._client = client or httpx.AsyncClient(base_url=API, timeout=timeout)
        self._client.headers.update(headers)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> GitHubClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            try:
                message = response.json().get("message", response.text)
            except ValueError:
                message = response.text
            raise GitHubError(response.status_code, str(message)[:300])
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    # ------------------------------------------------------------------ reads

    async def get_repo(self, ref: RepoRef) -> dict[str, Any]:
        return await self._request("GET", f"/repos/{ref.full_name}")

    async def get_last_commit_date(self, ref: RepoRef, branch: str | None) -> datetime | None:
        params: dict[str, Any] = {"per_page": 1}
        if branch:
            params["sha"] = branch
        commits = await self._request("GET", f"/repos/{ref.full_name}/commits", params=params)
        if not commits:
            return None
        commit = commits[0].get("commit", {})
        return _parse_dt(
            (commit.get("committer") or {}).get("date") or (commit.get("author") or {}).get("date")
        )

    async def vitals(self, ref: RepoRef) -> VitalRecords:
        repo = await self.get_repo(ref)
        branch = repo.get("default_branch")
        try:
            last_commit = await self.get_last_commit_date(ref, branch)
        except GitHubError:
            last_commit = None
        license_info = repo.get("license") or {}
        return VitalRecords(
            full_name=repo.get("full_name", ref.full_name),
            url=repo.get("html_url", ref.html_url),
            description=repo.get("description"),
            created_at=_parse_dt(repo.get("created_at")),
            pushed_at=_parse_dt(repo.get("pushed_at")),
            last_commit_at=last_commit or _parse_dt(repo.get("pushed_at")),
            stars=repo.get("stargazers_count"),
            forks=repo.get("forks_count"),
            open_issues=repo.get("open_issues_count"),
            archived=repo.get("archived"),
            default_branch=branch,
            license=license_info.get("spdx_id") or license_info.get("name"),
            api_available=True,
        )

    async def whoami(self) -> str:
        user = await self._request("GET", "/user")
        return str(user["login"])

    # ------------------------------------------------------------------ writes

    async def ensure_fork(
        self, ref: RepoRef, *, poll_seconds: float = 2.0, attempts: int = 30
    ) -> RepoRef:
        """Fork `ref` into the token owner's account and wait until it is ready."""
        login = await self.whoami()
        if login.lower() == ref.owner.lower():
            return ref
        fork = await self._request("POST", f"/repos/{ref.full_name}/forks", json={})
        fork_ref = RepoRef(owner=fork["owner"]["login"], name=fork["name"])
        for _ in range(attempts):
            try:
                await self.get_repo(fork_ref)
                return fork_ref
            except GitHubError as exc:
                if exc.status != 404:
                    raise
            await asyncio.sleep(poll_seconds)
        raise GitHubError(504, f"fork {fork_ref.full_name} was not ready in time")

    async def open_pull_request(
        self, ref: RepoRef, *, head: str, base: str, title: str, body: str
    ) -> str:
        pr = await self._request(
            "POST",
            f"/repos/{ref.full_name}/pulls",
            json={"title": title, "head": head, "base": base, "body": body},
        )
        return str(pr["html_url"])
