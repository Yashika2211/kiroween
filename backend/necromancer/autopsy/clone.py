"""Shallow, size-capped git clone. Never runs hooks or code from the repo."""

from __future__ import annotations

import asyncio
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from necromancer.errors import CloneFailed, RepoTooLarge
from necromancer.github.urls import RepoRef

# Disable anything in git that could execute repository-controlled code or prompt for input.
_SAFE_GIT_ENV = {
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_LFS_SKIP_SMUDGE": "1",
    "GIT_ASKPASS": "/bin/echo",
}
_SAFE_GIT_FLAGS = [
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "protocol.file.allow=never",
    "-c",
    "submodule.recurse=false",
]


def _git_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG", "TMPDIR"}}
    env.update(_SAFE_GIT_ENV)
    return env


async def run_git(*args: str, cwd: Path | None = None, timeout: float = 60.0) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git",
        *_SAFE_GIT_FLAGS,
        *args,
        cwd=cwd,
        env=_git_env(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise CloneFailed(f"git {args[0]} timed out after {timeout:.0f}s") from exc
    if proc.returncode != 0:
        message = err.decode(errors="replace").strip().splitlines()
        raise CloneFailed(message[-1] if message else f"git {args[0]} failed")
    return out.decode(errors="replace")


def dir_size_bytes(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            fp = Path(root) / name
            if not fp.is_symlink():
                total += fp.stat().st_size
    return total


async def clone_repo(ref: RepoRef, dest: Path, *, max_mb: int = 50, depth: int = 50) -> Path:
    """Clone `ref` into `dest` and return it. Raises RepoTooLarge over `max_mb`."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    await run_git(
        "clone",
        "--depth",
        str(depth),
        "--single-branch",
        "--no-tags",
        "--filter=blob:limit=5m",
        ref.clone_url,
        str(dest),
        timeout=90,
    )
    size_mb = dir_size_bytes(dest) / (1024 * 1024)
    if size_mb > max_mb:
        shutil.rmtree(dest, ignore_errors=True)
        raise RepoTooLarge(f"Repository is {size_mb:.0f} MB on disk; the limit is {max_mb} MB.")
    return dest


async def last_commit_date(repo_dir: Path) -> datetime | None:
    try:
        out = await run_git("log", "-1", "--format=%cI", cwd=repo_dir, timeout=10)
    except CloneFailed:
        return None
    text = out.strip()
    return datetime.fromisoformat(text).astimezone(UTC) if text else None


async def first_commit_date(repo_dir: Path) -> datetime | None:
    """Oldest commit reachable in the (shallow) clone; a lower bound for 'born'."""
    try:
        out = await run_git("log", "--reverse", "--format=%cI", cwd=repo_dir, timeout=10)
    except CloneFailed:
        return None
    lines = out.strip().splitlines()
    return datetime.fromisoformat(lines[0]).astimezone(UTC) if lines else None
