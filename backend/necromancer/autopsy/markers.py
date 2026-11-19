"""Detect Python 2 / legacy-Python markers without importing or executing anything.

Detection is line-based over code whose string contents and comments have been blanked
out, so it works on files that no longer parse under Python 3.12.
"""

from __future__ import annotations

import ast
import warnings
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from necromancer.knowledge import ALL_CODE_RULES, RAW_SYNTAX_RULES
from necromancer.models import FileHealth, Marker
from necromancer.workspace import iter_python_files, read_text


def blank_strings_and_comments(source: str) -> list[str]:
    """Return source lines with string literal bodies replaced by spaces and comments removed.

    Line count and column positions are preserved. Quote characters are kept so that
    patterns like `print "x"` still look like a print statement followed by a string.
    Handles single, double and triple quotes (multi-line) and backslash escapes.
    """
    out: list[str] = []
    in_string: str | None = None  # the closing delimiter while inside a string
    for line in source.splitlines():
        buf: list[str] = []
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            if in_string:
                if ch == "\\":
                    buf.append("  " if i + 1 < n else " ")
                    i += 2
                    continue
                if line.startswith(in_string, i):
                    buf.append(in_string)
                    i += len(in_string)
                    in_string = None
                    continue
                buf.append(" ")
                i += 1
                continue
            if ch == "#":
                break
            if ch in ("'", '"'):
                delim = ch * 3 if line.startswith(ch * 3, i) else ch
                buf.append(delim)
                i += len(delim)
                in_string = delim
                continue
            buf.append(ch)
            i += 1
        # Single-quoted strings cannot span lines (without a continuation backslash).
        if in_string in ("'", '"') and not line.endswith("\\"):
            in_string = None
        out.append("".join(buf))
    return out


def check_parses(source: str) -> tuple[bool, str | None]:
    """Does this source parse with the running interpreter (3.12)?"""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ast.parse(source)
    except SyntaxError as exc:
        where = f"line {exc.lineno}" if exc.lineno else "unknown line"
        return False, f"{exc.msg} ({where})"
    except (ValueError, RecursionError) as exc:
        return False, str(exc)
    return True, None


def scan_source(source: str, rel_path: str) -> list[Marker]:
    markers: list[Marker] = []
    raw_lines = source.splitlines()
    code_lines = blank_strings_and_comments(source)
    seen: set[tuple[int, str]] = set()

    for lineno, (raw, code) in enumerate(zip(raw_lines, code_lines, strict=False), start=1):
        if not code.strip() and not raw.strip():
            continue
        for rule in ALL_CODE_RULES:
            if rule.pattern.search(code) and (lineno, rule.kind) not in seen:
                seen.add((lineno, rule.kind))
                markers.append(
                    Marker(
                        file=rel_path,
                        line=lineno,
                        kind=rule.kind,
                        category=rule.category,
                        excerpt=raw.strip()[:160],
                        hint=rule.hint,
                    )
                )
        for rule in RAW_SYNTAX_RULES:
            if rule.pattern.search(raw) and (lineno, rule.kind) not in seen:
                seen.add((lineno, rule.kind))
                markers.append(
                    Marker(
                        file=rel_path,
                        line=lineno,
                        kind=rule.kind,
                        category=rule.category,
                        excerpt=raw.strip()[:160],
                        hint=rule.hint,
                    )
                )
    return markers


def _suppress_false_positives(markers: list[Marker], parses: bool) -> list[Marker]:
    """A file that parses under 3.12 cannot contain pure-syntax Python 2 constructs."""
    if not parses:
        return markers
    syntax_only = {
        "print_statement",
        "except_comma",
        "backticks",
        "ne_operator",
        "exec_statement",
        "octal_literal",
        "long_suffix",
        "ur_prefix",
        "tuple_parameter",
        "raise_comma",
    }
    return [m for m in markers if m.kind not in syntax_only]


@dataclass
class MarkerScan:
    files: list[FileHealth] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        return dict(Counter(m.kind for m in self.markers).most_common())

    @property
    def unparseable(self) -> list[FileHealth]:
        return [f for f in self.files if not f.parses]


def scan_repo(root: Path) -> MarkerScan:
    scan = MarkerScan()
    for path in iter_python_files(root):
        rel = path.relative_to(root).as_posix()
        source = read_text(path)
        parses, error = check_parses(source)
        lines = sum(1 for line in source.splitlines() if line.strip())
        scan.files.append(FileHealth(path=rel, lines=lines, parses=parses, error=error))
        scan.markers.extend(_suppress_false_positives(scan_source(source, rel), parses))
    return scan
