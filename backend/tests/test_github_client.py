import httpx
import pytest
import respx

from necromancer.github.client import API, GitHubClient, GitHubError
from necromancer.github.urls import RepoRef

REF = RepoRef("nvie", "times")


@respx.mock
async def test_vitals_combines_repo_and_last_commit() -> None:
    respx.get(f"{API}/repos/nvie/times").respond(
        json={
            "full_name": "nvie/times",
            "html_url": "https://github.com/nvie/times",
            "description": "Times and time zones",
            "created_at": "2012-02-14T10:00:00Z",
            "pushed_at": "2014-08-24T08:00:00Z",
            "stargazers_count": 386,
            "forks_count": 30,
            "open_issues_count": 4,
            "archived": True,
            "default_branch": "master",
            "license": {"spdx_id": "BSD-2-Clause"},
        }
    )
    respx.get(f"{API}/repos/nvie/times/commits").respond(
        json=[{"commit": {"committer": {"date": "2014-08-20T12:00:00Z"}}}]
    )
    async with GitHubClient() as gh:
        vitals = await gh.vitals(REF)
    assert vitals.archived is True
    assert vitals.last_commit_at is not None and vitals.last_commit_at.year == 2014
    assert vitals.last_commit_at.month == 8 and vitals.last_commit_at.day == 20
    assert vitals.license == "BSD-2-Clause"
    assert vitals.stars == 386


@respx.mock
async def test_vitals_falls_back_to_pushed_at_when_commits_fail() -> None:
    respx.get(f"{API}/repos/nvie/times").respond(
        json={"full_name": "nvie/times", "pushed_at": "2014-08-24T08:00:00Z"}
    )
    respx.get(f"{API}/repos/nvie/times/commits").respond(status_code=409, json={"message": "empty"})
    async with GitHubClient() as gh:
        vitals = await gh.vitals(REF)
    assert vitals.last_commit_at is not None and vitals.last_commit_at.day == 24


@respx.mock
async def test_errors_carry_status_and_message() -> None:
    respx.get(f"{API}/repos/nvie/times").respond(status_code=403, json={"message": "rate limited"})
    async with GitHubClient() as gh:
        with pytest.raises(GitHubError) as info:
            await gh.get_repo(REF)
    assert info.value.status == 403
    assert "rate limited" in str(info.value)


@respx.mock
async def test_token_is_sent_as_bearer() -> None:
    route = respx.get(f"{API}/user").respond(json={"login": "me"})
    async with GitHubClient("secret-token") as gh:
        assert await gh.whoami() == "me"
    assert route.calls.last.request.headers["Authorization"] == "Bearer secret-token"


@respx.mock
async def test_ensure_fork_polls_until_ready() -> None:
    respx.get(f"{API}/user").respond(json={"login": "me"})
    respx.post(f"{API}/repos/nvie/times/forks").respond(
        status_code=202, json={"owner": {"login": "me"}, "name": "times"}
    )
    respx.get(f"{API}/repos/me/times").mock(
        side_effect=[httpx.Response(404, json={"message": "nope"}), httpx.Response(200, json={})]
    )
    async with GitHubClient("t") as gh:
        fork = await gh.ensure_fork(REF, poll_seconds=0)
    assert fork.full_name == "me/times"


@respx.mock
async def test_open_pull_request_returns_url() -> None:
    respx.post(f"{API}/repos/me/times/pulls").respond(
        status_code=201, json={"html_url": "https://github.com/me/times/pull/1"}
    )
    async with GitHubClient("t") as gh:
        url = await gh.open_pull_request(
            RepoRef("me", "times"), head="b", base="master", title="t", body="b"
        )
    assert url.endswith("/pull/1")
