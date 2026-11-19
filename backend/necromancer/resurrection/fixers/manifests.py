"""Rewrite dependency manifests: bump stale pins, swap dead packages, clear vulnerabilities.

Edits are textual and minimal so the pull request diff stays readable: comments, ordering and
unrelated lines are untouched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from necromancer.models import Dependency, DependencyStatus, Vulnerability


@dataclass(frozen=True)
class Change:
    canonical: str
    new_requirement: str | None  # None = remove the dependency
    reason: str


def _max_fixed(vulns: list[Vulnerability], canonical: str) -> str | None:
    best: Version | None = None
    for v in vulns:
        if canonicalize_name(v.package) != canonical or not v.fixed:
            continue
        try:
            fixed = Version(v.fixed)
        except InvalidVersion:
            continue
        if best is None or fixed > best:
            best = fixed
    return str(best) if best else None


def plan_changes(deps: list[Dependency], vulns: list[Vulnerability]) -> dict[str, Change]:
    changes: dict[str, Change] = {}
    for dep in deps:
        canonical = canonicalize_name(dep.name)
        fixed = _max_fixed(vulns, canonical)
        if dep.status is DependencyStatus.DEAD:
            if dep.replacement:
                changes[canonical] = Change(
                    canonical, dep.replacement, f"{dep.name} is dead; replaced by {dep.replacement}"
                )
            else:
                changes[canonical] = Change(
                    canonical, None, f"{dep.name} is now part of the standard library"
                )
            continue
        pinned_exact = "==" in dep.spec
        if dep.status is DependencyStatus.OUTDATED and dep.latest:
            target = dep.latest
            if fixed:
                try:
                    if Version(fixed) > Version(target):
                        target = fixed
                except InvalidVersion:
                    pass
            if pinned_exact:
                changes[canonical] = Change(
                    canonical, f"{dep.name}=={target}", f"{dep.pinned_version} → {target}"
                )
            elif fixed:
                changes[canonical] = Change(
                    canonical, f"{dep.name}>={fixed}", f"raise floor to {fixed} (vulnerability fix)"
                )
            else:
                # A bare `>=old` floor is satisfied by the newest release, but old floors often
                # predate Python 3 wheels; raise it so pip never picks an ancient sdist.
                changes[canonical] = Change(
                    canonical, f"{dep.name}>={target}", f"floor {dep.pinned_version} → {target}"
                )
        elif fixed:
            changes[canonical] = Change(
                canonical,
                f"{dep.name}>={fixed}",
                f"raise to {fixed} to clear known vulnerabilities",
            )
    return changes


def _render(change: Change, req: Requirement | None) -> str:
    assert change.new_requirement is not None
    text = change.new_requirement
    if req is not None and req.extras and "[" not in text:
        base = re.match(r"^[A-Za-z0-9._-]+", text)
        if base:
            text = f"{base.group(0)}[{','.join(sorted(req.extras))}]{text[base.end() :]}"
    if req is not None and req.marker:
        text += f"; {req.marker}"
    return text


def rewrite_requirements(text: str, changes: dict[str, Change]) -> tuple[str, list[str]]:
    """Rewrite a requirements.txt body. Returns (new_text, notes)."""
    out: list[str] = []
    notes: list[str] = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        body, sep, comment = stripped.partition(" #")
        if not body or body.startswith(("#", "-")):
            out.append(line)
            continue
        try:
            req = Requirement(re.sub(r"\(\s*([<>=!~][^)]*)\)", r"\1", body))
        except InvalidRequirement:
            out.append(line)
            continue
        change = changes.get(canonicalize_name(req.name))
        if change is None:
            out.append(line)
            continue
        newline = "\n" if line.endswith("\n") else ""
        tail = f"  #{comment}" if sep else ""
        if change.new_requirement is None:
            out.append(f"# {body}  # removed by Necromancer: {change.reason}{newline}")
        else:
            out.append(f"{_render(change, req)}{tail}{newline}")
        notes.append(f"{req.name}: {change.reason}")
    return "".join(out), notes


_LITERAL = re.compile(
    r"""(?P<q>['"])(?P<body>[A-Za-z0-9][A-Za-z0-9._\[\],-]*\s*(?:\(?\s*[<>=!~][^'"]*)?)(?P=q)"""
)


def rewrite_literal_requirements(text: str, changes: dict[str, Change]) -> tuple[str, list[str]]:
    """Rewrite requirement strings inside setup.py / setup.cfg / pyproject.toml.

    Only string literals that parse as requirements and name a changed package are touched.
    A removed dependency becomes an empty string marker that is then dropped from lists.
    """
    notes: list[str] = []

    def repl(match: re.Match[str]) -> str:
        body = match.group("body")
        try:
            req = Requirement(re.sub(r"\(\s*([<>=!~][^)]*)\)", r"\1", body))
        except InvalidRequirement:
            return match.group(0)
        change = changes.get(canonicalize_name(req.name))
        if change is None:
            return match.group(0)
        notes.append(f"{req.name}: {change.reason}")
        if change.new_requirement is None:
            return "__NECRO_REMOVED__"
        return f"{match.group('q')}{_render(change, req)}{match.group('q')}"

    new = _LITERAL.sub(repl, text)
    # Drop removed entries from list literals: `"x", __NECRO_REMOVED__,` → `"x",`
    new = re.sub(r"[ \t]*__NECRO_REMOVED__\s*,[ \t]*\n?", "", new)
    new = re.sub(r",\s*__NECRO_REMOVED__", "", new)
    new = new.replace("__NECRO_REMOVED__", "")
    return new, notes


def rewrite_setup_cfg(text: str, changes: dict[str, Change]) -> tuple[str, list[str]]:
    """setup.cfg lists requirements one per line (no quotes) under install_requires."""
    out: list[str] = []
    notes: list[str] = []
    in_requires = False
    for line in text.splitlines(keepends=True):
        if re.match(r"^\s*install_requires\s*=", line):
            in_requires = True
            out.append(line)
            continue
        if in_requires and (not line.strip() or not line[:1].isspace()):
            in_requires = False
        if in_requires and line.strip():
            rewritten, line_notes = rewrite_requirements(line.strip() + "\n", changes)
            if line_notes:
                indent = line[: len(line) - len(line.lstrip())]
                if rewritten.startswith("#"):
                    notes.extend(line_notes)
                    continue
                out.append(indent + rewritten)
                notes.extend(line_notes)
                continue
        out.append(line)
    return "".join(out), notes
