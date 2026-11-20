"""Command line: `necromancer serve | autopsy <url> | resurrect <url>`."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from necromancer.config import get_settings
from necromancer.db import JobStore
from necromancer.errors import NecromancerError
from necromancer.jobs import JobManager
from necromancer.models import JobStatus


def _print_event(kind: str, data: dict[str, Any]) -> None:
    if kind == "step" and data.get("state") == "done":
        detail = f" ({data['detail']})" if data.get("detail") else ""
        print(f"  ✓ {data.get('label', data.get('key'))}{detail}")
    elif kind == "task" and data.get("status") in {"done", "failed", "skipped"}:
        mark = {"done": "✓", "failed": "✗", "skipped": "·"}[data["status"]]
        print(f"  {mark} {data['title']}  {data.get('note', '')}")
    elif kind == "log":
        print(f"    {data['message']}")
    elif kind == "error":
        print(f"  ✗ {data['message']}", file=sys.stderr)


async def _follow(manager: JobManager, job_id: str) -> None:
    async for event in manager.bus.subscribe(job_id):
        _print_event(event.type, event.data)


async def run(url: str, *, resurrect: bool, as_json: bool) -> int:
    settings = get_settings()
    manager = JobManager(settings, JobStore(settings.db_path))
    job = await manager.summon(url)
    print(f"Summoning {job.repo} (job {job.id})…")
    await asyncio.gather(_follow(manager, job.id), manager.wait(job.id))
    job = manager.get(job.id)
    if job.status is not JobStatus.AUTOPSIED or job.certificate is None:
        print(f"✗ {job.error}", file=sys.stderr)
        return 1
    cert = job.certificate
    print(
        f"\nDecay {cert.decay_score}/100 ({cert.decay_label})\nCause of death: {cert.cause_of_death}"
    )
    if as_json and not resurrect:
        print(cert.model_dump_json(indent=2))
    if not resurrect:
        return 0
    print("\nBeginning the ritual…")
    await manager.resurrect(job.id)
    await asyncio.gather(_follow(manager, job.id), manager.wait(job.id))
    job = manager.get(job.id)
    result = job.result
    if result is None:
        print(f"✗ {job.error}", file=sys.stderr)
        return 1
    ok = bool(result.tests and result.tests.ok)
    print(f"\n{'Risen' if ok else 'Partially risen'}: {result.files_changed} files changed.")
    if result.pr_url:
        print(f"Pull request: {result.pr_url}")
    elif result.patch:
        path = f"{job.repo.replace('/', '-')}-resurrected.patch"
        Path(path).write_text(result.patch, encoding="utf-8")
        print(f"Patch written to {path}")
    if as_json:
        print(json.dumps(result.model_dump(mode="json", exclude={"patch"}), indent=2))
    return 0 if ok else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="necromancer", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    for name in ("autopsy", "resurrect"):
        p = sub.add_parser(name, help=f"{name} a GitHub repository")
        p.add_argument("url")
        p.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        uvicorn.run("necromancer.api.app:app", host=args.host, port=args.port)
        return 0
    try:
        return asyncio.run(run(args.url, resurrect=args.command == "resurrect", as_json=args.json))
    except NecromancerError as exc:
        print(f"✗ {exc.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
