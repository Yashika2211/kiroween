from pathlib import Path

import pytest

from necromancer.models import RunStatus
from necromancer.sandbox.runner import (
    OutputBuffer,
    SandboxConfig,
    SandboxRunner,
    build_install_args,
    build_test_args,
)

CFG = SandboxConfig()


def _flag_value(args: list[str], flag: str) -> list[str]:
    return [args[i + 1] for i, a in enumerate(args) if a == flag]


def test_test_phase_is_offline_readonly_and_unprivileged(tmp_path: Path) -> None:
    args = build_test_args(CFG, "job1", tmp_path)
    assert _flag_value(args, "--network") == ["none"]
    assert "--read-only" in args
    assert _flag_value(args, "--user") == ["1000:1000"]
    assert _flag_value(args, "--cap-drop") == ["ALL"]
    assert "no-new-privileges" in _flag_value(args, "--security-opt")
    assert _flag_value(args, "--pids-limit") == ["256"]
    mounts = _flag_value(args, "-v")
    assert f"{tmp_path.resolve()}:/src:ro" in mounts
    assert "necro-job1-venv:/venv:ro" in mounts


def test_install_phase_has_network_but_still_hardened(tmp_path: Path) -> None:
    args = build_install_args(CFG, "job1", tmp_path, ["requirements.txt"], phase="install")
    assert _flag_value(args, "--network") == ["bridge"]
    assert _flag_value(args, "--cap-drop") == ["ALL"]
    assert _flag_value(args, "--memory") == ["1g"]
    assert "necro-job1-venv:/venv" in _flag_value(args, "-v")


def test_no_host_environment_is_forwarded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    for args in (
        build_test_args(CFG, "j", tmp_path),
        build_install_args(CFG, "j", tmp_path, [], phase="install"),
    ):
        joined = " ".join(args)
        assert "secret" not in joined
        assert _flag_value(args, "-e") == ["HOME=/tmp"]
        assert "--env-file" not in args


def test_requirement_names_are_shell_quoted(tmp_path: Path) -> None:
    args = build_install_args(CFG, "j", tmp_path, ["req; rm -rf /.txt"], phase="install")
    assert "'req; rm -rf /.txt'" in args[-1]


def test_output_buffer_keeps_tail() -> None:
    buf = OutputBuffer(max_lines=3, max_bytes=100)
    buf.feed(b"1\n2\n3\n4\n5\n")
    assert buf.text() == "3\n4\n5"
    buf.feed(("x" * 2000).encode())
    assert len(buf.text()) <= 100


async def test_disabled_sandbox_skips() -> None:
    runner = SandboxRunner(SandboxConfig(enabled=False))
    result = await runner.test("j", Path("."))
    assert result.status is RunStatus.SKIPPED
    assert "disabled" in result.reason
