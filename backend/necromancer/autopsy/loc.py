"""Line counting and the repository size limit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from necromancer.errors import NotAPythonRepo, RepoTooLarge
from necromancer.workspace import iter_python_files, read_text


@dataclass(frozen=True)
class LineCount:
    files: int
    lines: int
    per_file: dict[str, int]


def count_code_lines(source: str) -> int:
    """Non-blank lines that are not pure comments."""
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def count_python_lines(root: Path) -> LineCount:
    per_file: dict[str, int] = {}
    for path in iter_python_files(root):
        per_file[path.relative_to(root).as_posix()] = count_code_lines(read_text(path))
    return LineCount(files=len(per_file), lines=sum(per_file.values()), per_file=per_file)


def enforce_limits(count: LineCount, max_lines: int) -> None:
    if count.files == 0:
        raise NotAPythonRepo("No Python files found. Necromancer only resurrects Python projects.")
    if count.lines > max_lines:
        raise RepoTooLarge(
            f"This crypt is too big to resurrect: {count.lines:,} lines of Python "
            f"(limit {max_lines:,}). Try a smaller project."
        )
