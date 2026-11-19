import subprocess
from pathlib import Path

import pytest

from necromancer.autopsy import clone as clone_mod
from necromancer.autopsy.clone import (
    clone_repo,
    dir_size_bytes,
    first_commit_date,
    last_commit_date,
)
from necromancer.errors import CloneFailed, RepoTooLarge
from necromancer.github.urls import RepoRef


def _make_repo(path: Path) -> None:
    path.mkdir()
    env = {
        "GIT_COMMITTER_DATE": "2013-03-12T10:00:00+00:00",
        "GIT_AUTHOR_DATE": "2013-03-12T10:00:00+00:00",
    }
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    (path / "m.py").write_text("print 'hi'\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        cwd=path,
        check=True,
        env={**env, "PATH": "/usr/bin:/bin:/opt/homebrew/bin"},
    )


async def test_commit_dates_from_local_repo(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    _make_repo(repo)
    last = await last_commit_date(repo)
    first = await first_commit_date(repo)
    assert last is not None and last.year == 2013
    assert first == last


async def test_clone_failure_is_typed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ref = RepoRef("definitely-not-a-user-xyz", "nope")
    monkeypatch.setattr(RepoRef, "clone_url", property(lambda self: str(tmp_path / "missing")))
    with pytest.raises(CloneFailed):
        await clone_repo(ref, tmp_path / "dest")


async def test_clone_enforces_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "src"
    _make_repo(src)

    async def fake_git(*args: str, **kwargs: object) -> str:
        dest = Path(args[-1])
        dest.mkdir(parents=True)
        (dest / "big.bin").write_bytes(b"0" * (2 * 1024 * 1024))
        return ""

    monkeypatch.setattr(clone_mod, "run_git", fake_git)
    with pytest.raises(RepoTooLarge):
        await clone_repo(RepoRef("a", "b"), tmp_path / "dest", max_mb=1)
    assert not (tmp_path / "dest").exists()


def test_dir_size(tmp_path: Path) -> None:
    (tmp_path / "f").write_bytes(b"x" * 10)
    assert dir_size_bytes(tmp_path) == 10
