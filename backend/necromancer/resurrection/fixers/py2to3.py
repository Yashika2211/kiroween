"""Python 2 → 3 rewrite using fissix (a maintained fork of lib2to3).

This is a pure text transformation: the code is parsed into a concrete syntax tree,
rewritten and printed back. Nothing from the repository is imported or executed.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from fissix import pygram
from fissix.pgen2.parse import ParseError
from fissix.pgen2.tokenize import TokenError
from fissix.refactor import RefactoringTool, get_fixers_from_package

logging.getLogger("RefactoringTool").setLevel(logging.ERROR)

_PKG = "fissix.fixes"

# Fixers that are safe on code that already parses as Python 3 (they only touch constructs
# that are dead in Python 3). Noisy fixers like `dict`, `map`, `filter`, `zip` and `xrange`
# wrap calls in list() and are only used on files that are genuinely Python 2.
SAFE_ON_PY3 = [
    "has_key",
    "raw_input",
    "basestring",
    "long",
    "imports",
    "imports2",
    "urllib",
    "renames",
    "getcwdu",
    "execfile",
    "intern",
    "reduce",
    "apply",
    "funcattrs",
    "itertools_imports",
    "exitfunc",
    "xreadlines",
    "standarderror",
    "sys_exc",
    "asserts",
]


@lru_cache(maxsize=2)
def _tool(full: bool) -> RefactoringTool:
    if full:
        fixers = get_fixers_from_package(_PKG)
    else:
        fixers = [f"{_PKG}.fix_{name}" for name in SAFE_ON_PY3]
    return RefactoringTool(fixers, options={"print_function": False})


@lru_cache(maxsize=1)
def _tool_print_function() -> RefactoringTool:
    """For files that already use `from __future__ import print_function`."""
    tool = RefactoringTool(get_fixers_from_package(_PKG), options={"print_function": True})
    tool.driver.grammar = pygram.python_grammar_no_print_statement
    return tool


class ConversionError(Exception):
    pass


def convert(source: str, name: str = "<module>", *, full: bool = True) -> str:
    """Return `source` rewritten for Python 3. `full=False` uses only conservative fixers."""
    if not source.strip():
        return source
    text = source if source.endswith("\n") else source + "\n"
    if full and "print_function" in source:
        tool = _tool_print_function()
    else:
        tool = _tool(full)
    try:
        tree = tool.refactor_string(text, name)
    except (ParseError, TokenError, IndentationError, SyntaxError) as exc:
        raise ConversionError(f"{name}: {exc}") from exc
    result = str(tree)
    return result if source.endswith("\n") else result.rstrip("\n")
