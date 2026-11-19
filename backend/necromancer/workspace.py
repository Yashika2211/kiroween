"""Per-job workspace layout and path-safety helpers.

```
<workspace_dir>/<job_id>/
    before/   pristine clone (never modified after the autopsy)
    after/    working copy the resurrection edits
```
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from necromancer.errors import UnsafePath

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".eggs",
    "site-packages",
}


@dataclass(frozen=True)
class Workspace:
    root: Path

    @classmethod
    def for_job(cls, base: Path, job_id: str) -> Workspace:
        if not job_id.replace("-", "").isalnum():
            raise UnsafePath(f"invalid job id {job_id!r}")
        return cls(root=(base / job_id).resolve())

    @property
    def before(self) -> Path:
        return self.root / "before"

    @property
    def after(self) -> Path:
        return self.root / "after"

    def prepare(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)

    def fork_working_copy(self) -> Path:
        """Copy `before/` to `after/` (without symlinks) and return the copy."""
        if self.after.exists():
            shutil.rmtree(self.after)
        shutil.copytree(self.before, self.after, symlinks=True)
        return self.after

    def destroy(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def safe_join(base: Path, relative: str | Path) -> Path:
    """Join `relative` onto `base`, refusing anything that escapes `base`."""
    base_resolved = base.resolve()
    candidate = (base_resolved / relative).resolve()
    if candidate != base_resolved and base_resolved not in candidate.parents:
        raise UnsafePath(f"path {str(relative)!r} escapes the workspace")
    return candidate


def iter_python_files(root: Path) -> list[Path]:
    """All regular `.py` files under root, skipping vendored/virtualenv dirs and symlinks."""
    found: list[Path] = []
    root_resolved = root.resolve()
    for path in sorted(root.rglob("*.py")):
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts[:-1]):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if root_resolved not in path.resolve().parents:
            continue
        found.append(path)
    return found


def read_text(path: Path, limit_bytes: int = 2_000_000) -> str:
    """Read a source file as text, tolerating legacy encodings."""
    data = path.read_bytes()[:limit_bytes]
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
