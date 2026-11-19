"""Quiet `ast.parse` helpers (old code is full of invalid escape sequences that warn)."""

from __future__ import annotations

import ast
import warnings


def parse_quietly(source: str) -> ast.Module:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ast.parse(source)


def parses(source: str) -> bool:
    try:
        parse_quietly(source)
    except (SyntaxError, ValueError, RecursionError):
        return False
    return True
