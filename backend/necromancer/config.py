"""Runtime configuration read from the environment (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, does not override real env vars."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    return int(value) if value else default


@dataclass(frozen=True)
class Settings:
    github_token: str | None
    anthropic_api_key: str | None
    llm_model: str
    db_path: Path
    workspace_dir: Path
    max_lines: int
    max_repo_mb: int
    max_fix_iterations: int
    sandbox_image: str
    sandbox_mode: str
    cors_origins: list[str] = field(default_factory=list)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def can_open_prs(self) -> bool:
        return bool(self.github_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    root = Path(__file__).resolve().parent.parent
    _load_dotenv(root / ".env")
    _load_dotenv(root.parent / ".env")
    return Settings(
        github_token=os.environ.get("GITHUB_TOKEN") or None,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        llm_model=os.environ.get("NECRO_LLM_MODEL", "claude-opus-5-5"),
        db_path=Path(os.environ.get("NECRO_DB_PATH", root / "data" / "necromancer.sqlite3")),
        workspace_dir=Path(os.environ.get("NECRO_WORKSPACE_DIR", root / "data" / "workspaces")),
        max_lines=_int("NECRO_MAX_LINES", 5000),
        max_repo_mb=_int("NECRO_MAX_REPO_MB", 50),
        max_fix_iterations=_int("NECRO_MAX_FIX_ITERATIONS", 3),
        sandbox_image=os.environ.get("NECRO_SANDBOX_IMAGE", "python:3.12-slim"),
        sandbox_mode=os.environ.get("NECRO_SANDBOX_MODE", "docker"),
        cors_origins=[
            o.strip()
            for o in os.environ.get("NECRO_CORS_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ],
    )
