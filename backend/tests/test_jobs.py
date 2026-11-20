import os
import time
from dataclasses import replace
from pathlib import Path

from necromancer.config import get_settings
from necromancer.db import JobStore
from necromancer.jobs import JobManager
from necromancer.sandbox.runner import SandboxConfig, SandboxRunner


def test_prune_workspaces_removes_only_stale_dirs(tmp_path: Path) -> None:
    settings = replace(
        get_settings(), workspace_dir=tmp_path, workspace_ttl_hours=1, db_path=tmp_path / "db"
    )
    manager = JobManager(
        settings, JobStore(":memory:"), sandbox=SandboxRunner(SandboxConfig(enabled=False))
    )
    old, fresh = tmp_path / "old1", tmp_path / "fresh1"
    old.mkdir()
    fresh.mkdir()
    (tmp_path / "file.txt").write_text("not a workspace")
    two_hours_ago = time.time() - 7200
    os.utime(old, (two_hours_ago, two_hours_ago))
    assert manager.prune_workspaces() == 1
    assert not old.exists() and fresh.exists() and (tmp_path / "file.txt").exists()


def test_prune_disabled_with_zero_ttl(tmp_path: Path) -> None:
    settings = replace(get_settings(), workspace_dir=tmp_path, workspace_ttl_hours=0)
    manager = JobManager(
        settings, JobStore(":memory:"), sandbox=SandboxRunner(SandboxConfig(enabled=False))
    )
    (tmp_path / "x").mkdir()
    assert manager.prune_workspaces(now=time.time() + 10**9) == 0
