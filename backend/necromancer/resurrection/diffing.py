"""Unified diffs between the original and resurrected files."""

from __future__ import annotations

import difflib

from necromancer.models import FileDiff, FixSource


def unified_diff(path: str, before: str, after: str, context: int = 3) -> str:
    lines = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=context,
    )
    out = []
    for line in lines:
        out.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
    return "".join(out)


def make_diff(path: str, before: str, after: str, source: FixSource) -> FileDiff | None:
    if before == after:
        return None
    text = unified_diff(path, before, after)
    added = sum(1 for ln in text.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in text.splitlines() if ln.startswith("-") and not ln.startswith("---"))
    return FileDiff(path=path, source=source, diff=text, added=added, removed=removed)
