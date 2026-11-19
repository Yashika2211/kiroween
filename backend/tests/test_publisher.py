import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from necromancer.github.urls import RepoRef
from necromancer.rise.publisher import publish

GIT_ENV = {"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "HOME": "/tmp"}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=GIT_ENV,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "after"
    root.mkdir()
    git(root, "init", "-q", "-b", "master")
    (root / "m.py").write_text('print "hi"\n')
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    (root / "m.py").write_text('print("hi")\n')
    (root / "new.txt").write_text("x\n")
    return root


@dataclass(frozen=True)
class LocalRef(RepoRef):
    path: str = ""

    @property
    def clone_url(self) -> str:  # type: ignore[override]
        return self.path


class FakeGitHub:
    def __init__(self, fork_path: Path) -> None:
        self.fork = LocalRef("me", "times", str(fork_path))
        self.prs: list[dict] = []

    async def ensure_fork(self, ref: RepoRef) -> RepoRef:
        return self.fork

    async def open_pull_request(self, ref: RepoRef, **kw: str) -> str:
        self.prs.append({"ref": ref.full_name, **kw})
        return "https://github.com/me/times/pull/1"


async def test_without_token_returns_patch_only(repo: Path) -> None:
    published = await publish(
        repo=repo,
        upstream=RepoRef("nvie", "times"),
        default_branch="master",
        job_id="abcdef123456",
        title="t",
        body="b",
        token=None,
    )
    assert published.pr_url is None
    assert published.branch == "necromancer/resurrect-abcdef12"
    assert '-print "hi"' in published.patch and '+print("hi")' in published.patch
    assert "new.txt" in published.patch


async def test_with_token_pushes_branch_and_opens_pr(repo: Path, tmp_path: Path) -> None:
    fork = tmp_path / "fork.git"
    subprocess.run(["git", "init", "-q", "--bare", str(fork)], check=True, env=GIT_ENV)
    gh = FakeGitHub(fork)
    published = await publish(
        repo=repo,
        upstream=RepoRef("nvie", "times"),
        default_branch="master",
        job_id="abcdef123456",
        title="Resurrect",
        body="body",
        token="ghp_secret",
        github=gh,  # type: ignore[arg-type]
    )
    assert published.pr_url == "https://github.com/me/times/pull/1"
    branches = git(fork, "branch", "--list")
    assert "necromancer/resurrect-abcdef12" in branches
    log = git(fork, "log", "-1", "--format=%an <%ae>%n%s", "necromancer/resurrect-abcdef12")
    assert log.startswith("Necromancer <necromancer@users.noreply.github.com>")
    assert gh.prs[0]["head"] == "necromancer/resurrect-abcdef12" and gh.prs[0]["base"] == "master"
    # the token is never persisted into the repository config
    assert "ghp_secret" not in (repo / ".git" / "config").read_text()
