"""Replace removed or renamed APIs that have a safe mechanical substitute.

Runs after the 2to3 pass, on code that parses under Python 3.12. Each rewrite is verified by
re-parsing; if the result does not parse, the original text is kept.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable

from necromancer.knowledge import API_RULES, UNITTEST_ALIASES
from necromancer.pyparse import parse_quietly

_ABC_NAMES = {
    "Mapping",
    "MutableMapping",
    "Sequence",
    "MutableSequence",
    "Set",
    "MutableSet",
    "Iterable",
    "Iterator",
    "Callable",
    "Hashable",
    "Sized",
    "Container",
    "Generator",
    "Awaitable",
    "Coroutine",
    "AsyncIterable",
    "AsyncIterator",
    "ItemsView",
    "KeysView",
    "ValuesView",
    "MappingView",
    "ByteString",
}

_IMPORT_LINE = re.compile(r"^(?:import|from)\s+\S")


def ensure_import(source: str, statement: str) -> str:
    """Insert `statement` after the module's leading docstring/comments/__future__/imports
    block, unless an identical line already exists."""
    lines = source.splitlines(keepends=True)
    if any(line.strip() == statement for line in lines):
        return source
    try:
        tree = parse_quietly(source)
    except SyntaxError:
        return source
    insert_at = 0
    body = tree.body
    idx = 0
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        insert_at = body[0].end_lineno or 0
        idx = 1
    while idx < len(body) and isinstance(body[idx], (ast.Import, ast.ImportFrom)):
        insert_at = body[idx].end_lineno or insert_at
        idx += 1
    newline = "\n"
    lines.insert(insert_at, statement + newline)
    return "".join(lines)


def _fix_collections_import(source: str) -> str:
    """`from collections import Mapping, OrderedDict` → split ABCs into collections.abc."""

    def repl(match: re.Match[str]) -> str:
        indent, names_text = match.group(1), match.group(2)
        stripped = names_text.strip().strip("()")
        names = [n.strip() for n in stripped.replace("\n", " ").split(",") if n.strip()]
        abc = [n for n in names if n.split(" as ")[0].strip() in _ABC_NAMES]
        rest = [n for n in names if n not in abc]
        if not abc:
            return match.group(0)
        out = []
        if rest:
            out.append(f"{indent}from collections import {', '.join(rest)}")
        out.append(f"{indent}from collections.abc import {', '.join(abc)}")
        return "\n".join(out)

    return re.sub(
        r"^([ \t]*)from\s+collections\s+import\s+(\([^)]*\)|[^\n]+)$",
        repl,
        source,
        flags=re.M,
    )


def _fix_collections_attr(source: str) -> str:
    rule = next(r for r in API_RULES if r.kind == "collections_abc")
    assert rule.fix is not None
    pattern, replacement = rule.fix
    new = pattern.sub(replacement, source)
    if new != source and not re.search(r"^\s*import\s+collections\.abc\b", new, flags=re.M):
        new = ensure_import(new, "import collections.abc")
    return new


def _fix_unittest_aliases(source: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return f"self.{UNITTEST_ALIASES[match.group(1)]}("

    alt = "|".join(sorted(UNITTEST_ALIASES, key=len, reverse=True))
    return re.sub(rf"\bself\.({alt})\s*\(", repl, source)


def _fix_simple_rules(source: str) -> str:
    for rule in API_RULES:
        if rule.fix and rule.kind != "collections_abc":
            pattern, replacement = rule.fix
            source = pattern.sub(replacement, source)
    uses_errno = re.search(r"(?<![\w.])errno\.\w", source)
    if uses_errno and not re.search(r"^\s*import\s+errno\b", source, flags=re.M):
        source = ensure_import(source, "import errno")
    return source


def _fix_with_import(pattern: str, replacement: str, statement: str) -> Callable[[str], str]:
    def fixer(source: str) -> str:
        new = re.sub(pattern, replacement, source)
        if new != source:
            new = ensure_import(new, statement)
        return new

    return fixer


def _fix_dict_iter(source: str) -> str:
    source = re.sub(r"\.iteritems\(\s*\)", ".items()", source)
    source = re.sub(r"\.itervalues\(\s*\)", ".values()", source)
    return re.sub(r"\.iterkeys\(\s*\)", ".keys()", source)


def _fix_xrange(source: str) -> str:
    return re.sub(r"(?<![\w.])xrange\s*\(", "range(", source)


def _fix_backport_imports(source: str) -> str:
    """mock → unittest.mock, unittest2 → unittest (both are dead PyPI backports)."""
    source = re.sub(
        r"^([ \t]*)import mock[ \t]*$", r"\1from unittest import mock", source, flags=re.M
    )
    source = re.sub(
        r"^([ \t]*)from mock import ", r"\1from unittest.mock import ", source, flags=re.M
    )
    source = re.sub(
        r"^([ \t]*)import unittest2 as unittest[ \t]*$", r"\1import unittest", source, flags=re.M
    )
    source = re.sub(
        r"^([ \t]*)import unittest2[ \t]*$", r"\1import unittest as unittest2", source, flags=re.M
    )
    return re.sub(
        r"^([ \t]*)from unittest2 import ", r"\1from unittest import ", source, flags=re.M
    )


def _fix_asyncio_coroutine(source: str) -> str:
    """`@asyncio.coroutine` + `yield from` → `async def` + `await` when the shape is simple."""
    pattern = re.compile(r"^([ \t]*)@asyncio\.coroutine[ \t]*\n\1def ", re.M)
    if not pattern.search(source):
        return source
    candidate = pattern.sub(r"\1async def ", source)
    candidate = re.sub(r"\byield from\b", "await", candidate)
    return candidate


FIXERS: list[tuple[str, Callable[[str], str]]] = [
    ("collections_abc_import", _fix_collections_import),
    ("collections_abc", _fix_collections_attr),
    ("unittest_aliases", _fix_unittest_aliases),
    ("simple_rules", _fix_simple_rules),
    ("dict_iter", _fix_dict_iter),
    ("xrange", _fix_xrange),
    ("backports", _fix_backport_imports),
    ("cgi_escape", _fix_with_import(r"\bcgi\.escape\s*\(", "html.escape(", "import html")),
    ("fractions_gcd", _fix_with_import(r"\bfractions\.gcd\s*\(", "math.gcd(", "import math")),
    (
        "html_parser_unescape",
        _fix_with_import(r"\bHTMLParser\(\)\.unescape\s*\(", "html.unescape(", "import html"),
    ),
    (
        "yaml_load",
        lambda s: re.sub(r"\byaml\.load\s*\(((?:(?!Loader)[^()])*)\)", r"yaml.safe_load(\1)", s),
    ),
    ("asyncio_coroutine", _fix_asyncio_coroutine),
]


def _parses(source: str) -> bool:
    try:
        parse_quietly(source)
    except SyntaxError:
        return False
    return True


def apply_api_fixes(source: str) -> tuple[str, list[str]]:
    """Apply every fixer whose result still parses. Returns (new_source, applied_names)."""
    if not _parses(source):
        return source, []
    applied: list[str] = []
    for name, fixer in FIXERS:
        candidate = fixer(source)
        if candidate != source and _parses(candidate):
            source = candidate
            applied.append(name)
    return source, applied
