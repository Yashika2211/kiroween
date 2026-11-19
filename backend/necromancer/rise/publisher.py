"""Commit the resurrected tree, push it to a fork and open a pull request.

The GitHub token never touches disk or a remote URL: git asks for credentials through a
GIT_ASKPASS helper that echoes an environment variable set only on the push subprocess.
"""

from __future__ import annotations

import asyncio
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from necromancer.github.client import GitHubClient
from necromancer.github.urls import RepoRef

BOT_NAME = "Necromancer"
BOT_EMAIL = "necromancer@users.noreply.github.com"

_ASKPASS = """#!/bin/sh
case "$1" in
  Username*) echo "x-access-token" ;;
  *) echo "$NECRO_GIT_TOKEN" ;;
esac
"""


class PublishError(Exception):
    pass


async def _git(
    repo: Path, *args: str, env: dict[str, str] | None = None, timeout: float = 120
) -> str:
    base_env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG", "TMPDIR"}}
    base_env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"})
    base_env.update(env or {})
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        *args,
        cwd=repo,
        env=base_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError as exc:
        proc.kill()
        raise PublishError(f"git {args[0]} timed out") from exc
    if proc.returncode != 0:
        message = err.decode(errors="replace").strip()
        # Never echo anything that might contain the token.
        message = message.replace(base_env.get("NECRO_GIT_TOKEN", "\0"), "***")
        raise PublishError(f"git {args[0]} failed: {message[-400:]}")
    return out.decode(errors="replace")


async def commit_all(repo: Path, branch: str, message: str) -> None:
    await _git(repo, "checkout", "-q", "-B", branch)
    await _git(repo, "add", "-A")
    await _git(
        repo,
        "-c",
        f"user.name={BOT_NAME}",
        "-c",
        f"user.email={BOT_EMAIL}",
        "commit",
        "-q",
        "--no-verify",
        "-m",
        message,
    )


async def make_patch(repo: Path) -> str:
    """Patch of every change in the working tree relative to the cloned HEAD."""
    await _git(repo, "add", "-A")
    return await _git(repo, "diff", "--cached", "--no-color", "--binary", "HEAD")


async def push(repo: Path, fork: RepoRef, branch: str, token: str) -> None:
    with tempfile.TemporaryDirectory(prefix="necro-askpass-") as tmp:
        helper = Path(tmp) / "askpass.sh"
        helper.write_text(_ASKPASS)
        helper.chmod(stat.S_IRWXU)
        await _git(
            repo,
            "push",
            "--force",
            "--no-verify",
            fork.clone_url,
            f"HEAD:refs/heads/{branch}",
            env={"GIT_ASKPASS": str(helper), "NECRO_GIT_TOKEN": token},
            timeout=180,
        )


@dataclass(frozen=True)
class Published:
    pr_url: str | None
    branch: str
    fork: str | None
    patch: str | None


async def publish(
    *,
    repo: Path,
    upstream: RepoRef,
    default_branch: str,
    job_id: str,
    title: str,
    body: str,
    token: str | None,
    github: GitHubClient | None = None,
) -> Published:
    branch = f"necromancer/resurrect-{job_id[:8]}"
    patch = await make_patch(repo)
    if not token:
        return Published(pr_url=None, branch=branch, fork=None, patch=patch)
    await commit_all(repo, branch, title)
    gh = github or GitHubClient(token)
    try:
        fork = await gh.ensure_fork(upstream)
        await push(repo, fork, branch, token)
        # The PR targets the fork's own default branch so it never notifies the
        # (abandoned) upstream maintainers without the user choosing to.
        pr_url = await gh.open_pull_request(
            fork, head=branch, base=default_branch, title=title, body=body
        )
    finally:
        if github is None:
            await gh.aclose()
    return Published(pr_url=pr_url, branch=branch, fork=fork.full_name, patch=patch)
