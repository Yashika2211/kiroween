"""Parse dependency declarations from requirements files, setup.py, setup.cfg and pyproject.

`setup.py` is read with `ast` only: it is never imported or executed.
"""

from __future__ import annotations

import ast
import configparser
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from necromancer.pyparse import parse_quietly
from necromancer.workspace import read_text, safe_join

_REQ_FILE_GLOBS = ["requirements*.txt", "requirements/*.txt", "*requirements.txt", "reqs/*.txt"]
_SKIP_PREFIXES = ("-e ", "--", "git+", "hg+", "svn+", "http://", "https://", "file:")


@dataclass(frozen=True)
class DeclaredDependency:
    name: str
    canonical: str
    spec: str
    pinned_version: str | None
    minimum_version: str | None
    source: str
    line: int | None = None


def _pinned(req: Requirement) -> tuple[str | None, str | None]:
    pinned: str | None = None
    minimum: str | None = None
    for spec in req.specifier:
        if spec.operator in ("==", "===") and "*" not in spec.version:
            pinned = spec.version
        elif spec.operator in (">=", "~=", "=="):
            minimum = spec.version.rstrip(".*")
    return pinned, minimum or pinned


def parse_requirement(text: str, source: str, line: int | None = None) -> DeclaredDependency | None:
    """Parse one PEP 508 requirement string. Returns None for things we can't interpret."""
    cleaned = text.split(" #", 1)[0].strip()
    if not cleaned or cleaned.startswith("#") or cleaned.startswith(_SKIP_PREFIXES):
        return None
    # Old-style "pkg >= 1.0, < 2" and "pkg (>=1.0)" forms
    cleaned = re.sub(r"\(\s*([<>=!~][^)]*)\)", r"\1", cleaned)
    try:
        req = Requirement(cleaned)
    except InvalidRequirement:
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", cleaned)
        if not match:
            return None
        return DeclaredDependency(
            name=match.group(1),
            canonical=canonicalize_name(match.group(1)),
            spec=cleaned,
            pinned_version=None,
            minimum_version=None,
            source=source,
            line=line,
        )
    pinned, minimum = _pinned(req)
    return DeclaredDependency(
        name=req.name,
        canonical=canonicalize_name(req.name),
        spec=str(req.specifier),
        pinned_version=pinned,
        minimum_version=minimum,
        source=source,
        line=line,
    )


def parse_requirements_file(
    path: Path, root: Path, _seen: set[Path] | None = None
) -> list[DeclaredDependency]:
    seen = _seen if _seen is not None else set()
    resolved = path.resolve()
    if resolved in seen or not path.is_file():
        return []
    seen.add(resolved)
    rel = path.relative_to(root).as_posix()
    deps: list[DeclaredDependency] = []
    for lineno, raw in enumerate(read_text(path).splitlines(), start=1):
        line = raw.strip()
        if line.startswith(("-r ", "--requirement ")):
            include = line.split(maxsplit=1)[1].strip()
            # Includes may point at sibling dirs, but never outside the repository root.
            rel_include = (
                (path.parent / include).resolve().relative_to(root.resolve(), walk_up=True)
            )
            if rel_include.parts[:1] == ("..",):
                continue
            deps.extend(parse_requirements_file(safe_join(root, rel_include), root, seen))
            continue
        dep = parse_requirement(line, rel, lineno)
        if dep:
            deps.append(dep)
    return deps


def _literal_strings(node: ast.AST, assignments: dict[str, ast.AST]) -> list[str]:
    """Best-effort extraction of a list of string literals from an AST node."""
    if isinstance(node, ast.Name) and node.id in assignments:
        return _literal_strings(assignments[node.id], assignments)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values: list[str] = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                values.append(elt.value)
        return values
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _literal_strings(node.left, assignments) + _literal_strings(node.right, assignments)
    return []


def parse_setup_py(path: Path, root: Path) -> list[DeclaredDependency]:
    """Extract install_requires from setup.py using ast. Unparseable (py2) files are retried
    after a crude print-statement rewrite so we can still read the literal lists."""
    source = read_text(path)
    try:
        tree = parse_quietly(source)
    except SyntaxError:
        patched = re.sub(r"^(\s*)print\s+(.+)$", r"\1print(\2)", source, flags=re.M)
        try:
            tree = parse_quietly(patched)
        except SyntaxError:
            return []
    assignments: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                assignments[target.id] = node.value
    rel = path.relative_to(root).as_posix()
    deps: list[DeclaredDependency] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg in {"install_requires", "requires"}:
                for text in _literal_strings(kw.value, assignments):
                    dep = parse_requirement(text, rel, getattr(kw.value, "lineno", None))
                    if dep:
                        deps.append(dep)
    return deps


def parse_setup_cfg(path: Path, root: Path) -> list[DeclaredDependency]:
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(read_text(path))
    except configparser.Error:
        return []
    raw = parser.get("options", "install_requires", fallback="")
    rel = path.relative_to(root).as_posix()
    return [d for line in raw.splitlines() if (d := parse_requirement(line, rel))]


def parse_pyproject(path: Path, root: Path) -> list[DeclaredDependency]:
    try:
        data = tomllib.loads(read_text(path))
    except tomllib.TOMLDecodeError:
        return []
    rel = path.relative_to(root).as_posix()
    deps: list[DeclaredDependency] = []
    for text in data.get("project", {}).get("dependencies", []) or []:
        if dep := parse_requirement(str(text), rel):
            deps.append(dep)
    poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {}) or {}
    for name, value in poetry.items():
        if name.lower() == "python":
            continue
        version = value if isinstance(value, str) else (value or {}).get("version", "")
        version = str(version).replace("^", ">=").replace("~", "~=") if version != "*" else ""
        if dep := parse_requirement(f"{name}{version}", rel):
            deps.append(dep)
    return deps


def find_dependencies(root: Path) -> list[DeclaredDependency]:
    """All declared runtime dependencies, de-duplicated by canonical name.

    When a package appears in several files, the entry with a pinned version wins, then the
    first one found (requirements files are read first).
    """
    seen_files: set[Path] = set()
    collected: list[DeclaredDependency] = []
    for pattern in _REQ_FILE_GLOBS:
        for path in sorted(root.glob(pattern)):
            if "dev" in path.name or "test" in path.name or "doc" in path.name:
                continue
            collected.extend(parse_requirements_file(path, root, seen_files))
    for name, parser in (
        ("setup.py", parse_setup_py),
        ("setup.cfg", parse_setup_cfg),
        ("pyproject.toml", parse_pyproject),
    ):
        path = root / name
        if path.is_file() and not path.is_symlink():
            collected.extend(parser(path, root))

    best: dict[str, DeclaredDependency] = {}
    for dep in collected:
        current = best.get(dep.canonical)
        if current is None or (current.pinned_version is None and dep.pinned_version):
            best[dep.canonical] = dep
    return list(best.values())


def find_dev_dependencies(root: Path) -> list[DeclaredDependency]:
    """Test/dev requirements, used to install test runners inside the sandbox."""
    deps: list[DeclaredDependency] = []
    seen: set[Path] = set()
    for pattern in _REQ_FILE_GLOBS:
        for path in sorted(root.glob(pattern)):
            if "dev" in path.name or "test" in path.name:
                deps.extend(parse_requirements_file(path, root, seen))
    return deps
