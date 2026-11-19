"""Run pyupgrade --py312-plus on source text.

pyupgrade only tokenizes and parses; it never imports the code it rewrites.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from necromancer.pyparse import parse_quietly


def pyupgrade(source: str, *, timeout: float = 30.0) -> str:
    """Return the pyupgrade'd source, or the input unchanged if it can't be processed."""
    try:
        parse_quietly(source)
    except SyntaxError:
        return source
    with tempfile.TemporaryDirectory(prefix="necro-pyupgrade-") as tmp:
        path = Path(tmp) / "module.py"
        path.write_text(source, encoding="utf-8")
        try:
            subprocess.run(
                [sys.executable, "-m", "pyupgrade", "--py312-plus", str(path)],
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return source
        result = path.read_text(encoding="utf-8")
    try:
        parse_quietly(result)
    except SyntaxError:
        return source
    return result
