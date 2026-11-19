import ast

import pytest

from necromancer.resurrection.fixers.py2to3 import ConversionError, convert

PY2 = """\
import urllib2
from StringIO import StringIO

def f(d):
    print "items:", len(d)
    for k, v in d.iteritems():
        if d.has_key(k) and isinstance(v, basestring):
            print >>sys.stderr, k
    try:
        x = 0755 + 10L
    except ValueError, e:
        raise TypeError, "bad"
    return `x`
"""


def test_full_conversion_parses_on_py312() -> None:
    out = convert(PY2, "m.py")
    ast.parse(out)
    assert 'print("items:", len(d))' in out
    assert "except ValueError as e:" in out
    assert 'raise TypeError("bad")' in out
    assert "0o755" in out
    assert "import urllib.request" in out
    assert "from io import StringIO" in out
    assert "isinstance(v, str)" in out
    assert "repr(x)" in out


def test_print_function_files_keep_their_calls() -> None:
    src = 'from __future__ import print_function\nprint("a", end="")\n'
    assert 'print("a", end="")' in convert(src, "m.py")


def test_conservative_mode_leaves_py3_code_alone() -> None:
    src = "def f(d):\n    return list(d.keys()), range(3), map(str, [1])\n"
    assert convert(src, "m.py", full=False) == src


def test_conservative_mode_still_fixes_dead_builtins() -> None:
    src = "x = raw_input('?')\nok = d.has_key(1)\n"
    out = convert(src, "m.py", full=False)
    assert "input('?')" in out and "1 in d" in out


def test_preserves_missing_trailing_newline() -> None:
    assert convert("x = 1", "m.py") == "x = 1"


def test_empty_source() -> None:
    assert convert("", "m.py") == ""


def test_garbage_raises_conversion_error() -> None:
    with pytest.raises(ConversionError):
        convert("def (:\n", "bad.py")
