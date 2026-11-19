"""Run untrusted repository code inside throwaway Docker containers.

Two phases share a per-job named volume holding a virtualenv:

* install: network on, runs as root inside the container (the venv volume is root-owned),
  all capabilities dropped. Creates /venv, installs test tools, requirements and the repo.
* test:    network off, read-only root filesystem, unprivileged user. Copies the repo into a
  tmpfs and runs pytest there so the mounted source stays read-only.

Nothing from the host environment is forwarded into containers.
"""

from __future__ import annotations

import asyncio
import shlex
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from necromancer.models import RunResult, RunStatus

TAIL_LINES = 60
TAIL_BYTES = 16_000

HARDENING_FLAGS = [
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
    "--memory",
    "1g",
    "--memory-swap",
    "1g",
    "--cpus",
    "1",
    "--pids-limit",
    "256",
]

INSTALL_SCRIPT = r"""
set -u
export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_INPUT=1 PIP_ROOT_USER_ACTION=ignore
[ -n "$(ls -A /src 2>/dev/null)" ] || {
  echo "sandbox: /src is empty; is the workspace directory shared with the Docker VM?"
  exit 91
}
echo "--- python -m venv /venv ($(python -V))"
python -m venv /venv
/venv/bin/pip install -q pytest hypothesis || exit 90
rm -rf /tmp/build && cp -r /src /tmp/build && cd /tmp/build
status=0
for req in {requirements}; do
  if [ -f "$req" ]; then
    echo "--- pip install -r $req"
    /venv/bin/pip install -r "$req" || status=$?
  fi
done
if [ -f setup.py ] || [ -f pyproject.toml ]; then
  echo "--- pip install ."
  /venv/bin/pip install . || status=$?
fi
exit $status
"""

TEST_SCRIPT = r"""
set -u
[ -n "$(ls -A /src 2>/dev/null)" ] || {
  echo "sandbox: /src is empty; is the workspace directory shared with the Docker VM?"
  exit 91
}
rm -rf /tmp/run && cp -r /src /tmp/run && cd /tmp/run
export PYTHONPATH=/tmp/run PYTHONDONTWRITEBYTECODE=1 HYPOTHESIS_NO_TRACEBACK_TRIM=1
/venv/bin/python -m pytest -q -x --no-header -p no:cacheprovider \
  -W ignore::DeprecationWarning {targets}
"""


class OutputBuffer:
    """Keeps only the last N lines / bytes of a stream."""

    def __init__(self, max_lines: int = TAIL_LINES, max_bytes: int = TAIL_BYTES) -> None:
        self._lines: deque[str] = deque(maxlen=max_lines)
        self._max_bytes = max_bytes

    def feed(self, chunk: bytes) -> None:
        for line in chunk.decode(errors="replace").splitlines():
            self._lines.append(line[:500])

    def text(self) -> str:
        joined = "\n".join(self._lines)
        return joined[-self._max_bytes :]


@dataclass(frozen=True)
class SandboxConfig:
    image: str = "python:3.12-slim"
    install_timeout: float = 180.0
    test_timeout: float = 120.0
    probe_timeout: float = 25.0
    enabled: bool = True


def volume_name(job_id: str) -> str:
    return f"necro-{job_id}-venv"


def container_name(job_id: str, phase: str) -> str:
    return f"necro-{job_id}-{phase}"


def build_install_args(
    cfg: SandboxConfig, job_id: str, repo_dir: Path, requirements: list[str], *, phase: str
) -> list[str]:
    script = INSTALL_SCRIPT.format(requirements=" ".join(shlex.quote(r) for r in requirements))
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name(job_id, phase),
        *HARDENING_FLAGS,
        "--network",
        "bridge",
        "--tmpfs",
        "/tmp:rw,exec,size=1g",
        "-v",
        f"{volume_name(job_id)}:/venv",
        "-v",
        f"{repo_dir.resolve()}:/src:ro",
        "-e",
        "HOME=/tmp",
        cfg.image,
        "sh",
        "-c",
        script,
    ]


def build_test_args(
    cfg: SandboxConfig, job_id: str, repo_dir: Path, targets: list[str] | None = None
) -> list[str]:
    script = TEST_SCRIPT.format(targets=" ".join(shlex.quote(t) for t in (targets or [])))
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        container_name(job_id, "test"),
        *HARDENING_FLAGS,
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,exec,size=256m",
        "--user",
        "1000:1000",
        "-v",
        f"{volume_name(job_id)}:/venv:ro",
        "-v",
        f"{repo_dir.resolve()}:/src:ro",
        "-e",
        "HOME=/tmp",
        cfg.image,
        "sh",
        "-c",
        script,
    ]


async def _run(args: list[str], timeout: float, kill_name: str | None) -> RunResult:
    started = time.monotonic()
    last_line = args[-1].strip().splitlines()[-1] if args else ""
    command = f"docker run … {last_line[:160]}"
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={"PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"},
        )
    except FileNotFoundError:
        return RunResult(status=RunStatus.SKIPPED, reason="docker CLI not found", command=command)
    buffer = OutputBuffer()

    async def pump() -> None:
        assert proc.stdout is not None
        while chunk := await proc.stdout.read(4096):
            buffer.feed(chunk)

    try:
        await asyncio.wait_for(asyncio.gather(pump(), proc.wait()), timeout=timeout)
    except TimeoutError:
        if kill_name:
            await _quiet("docker", "rm", "-f", kill_name)
        proc.kill()
        await proc.wait()
        return RunResult(
            status=RunStatus.TIMEOUT,
            exit_code=None,
            duration_s=round(time.monotonic() - started, 2),
            command=command,
            tail=buffer.text(),
            reason=f"killed after {timeout:.0f}s",
        )
    code = proc.returncode
    return RunResult(
        status=RunStatus.PASSED if code == 0 else RunStatus.FAILED,
        exit_code=code,
        duration_s=round(time.monotonic() - started, 2),
        command=command,
        tail=buffer.text(),
    )


async def _quiet(*args: str) -> int:
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
    except FileNotFoundError:
        return 127
    try:
        return await asyncio.wait_for(proc.wait(), timeout=20)
    except TimeoutError:
        proc.kill()
        return 124


class SandboxRunner:
    def __init__(self, cfg: SandboxConfig | None = None) -> None:
        self.cfg = cfg or SandboxConfig()
        self._available: bool | None = None

    async def available(self) -> bool:
        if not self.cfg.enabled:
            return False
        if self._available is None:
            self._available = await _quiet("docker", "info") == 0
        return self._available

    async def _skip_reason(self) -> RunResult | None:
        if not self.cfg.enabled:
            return RunResult(status=RunStatus.SKIPPED, reason="sandbox disabled by configuration")
        if not await self.available():
            return RunResult(status=RunStatus.SKIPPED, reason="Docker is not available")
        return None

    async def install(
        self, job_id: str, repo_dir: Path, requirements: list[str], *, phase: str = "install"
    ) -> RunResult:
        if skipped := await self._skip_reason():
            return skipped
        timeout = self.cfg.probe_timeout if phase == "probe" else self.cfg.install_timeout
        args = build_install_args(self.cfg, job_id, repo_dir, requirements, phase=phase)
        return await _run(args, timeout, container_name(job_id, phase))

    async def test(
        self, job_id: str, repo_dir: Path, targets: list[str] | None = None
    ) -> RunResult:
        if skipped := await self._skip_reason():
            return skipped
        args = build_test_args(self.cfg, job_id, repo_dir, targets)
        result = await _run(args, self.cfg.test_timeout, container_name(job_id, "test"))
        # pytest exit code 5 = no tests collected
        if result.exit_code == 5:
            result.status = RunStatus.FAILED
            result.reason = "no tests were collected"
        return result

    async def probe(self, job_id: str, repo_dir: Path, requirements: list[str]) -> RunResult:
        """Autopsy probe: does the original repo even install on 3.12? Uses its own volume."""
        probe_id = f"{job_id}-probe"
        try:
            return await self.install(probe_id, repo_dir, requirements, phase="probe")
        finally:
            await self.cleanup(probe_id)

    async def cleanup(self, job_id: str) -> None:
        if not await self.available():
            return
        for phase in ("install", "test", "probe"):
            await _quiet("docker", "rm", "-f", container_name(job_id, phase))
        await _quiet("docker", "volume", "rm", "-f", volume_name(job_id))
