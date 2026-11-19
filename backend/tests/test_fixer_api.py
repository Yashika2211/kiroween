import ast

from hypothesis import given
from hypothesis import strategies as st

from necromancer.resurrection.fixers.api import apply_api_fixes, ensure_import


def fix(src: str) -> str:
    out, _ = apply_api_fixes(src)
    ast.parse(out)
    return out


def test_collections_import_is_split() -> None:
    out = fix("from collections import OrderedDict, Mapping as M, Iterable\n")
    assert "from collections import OrderedDict\n" in out
    assert "from collections.abc import Mapping as M, Iterable" in out


def test_collections_attribute_gets_abc_import() -> None:
    out = fix('"""doc"""\nimport collections\n\nisinstance(x, collections.Mapping)\n')
    assert "collections.abc.Mapping" in out
    assert out.index("import collections.abc") > out.index('"""doc"""')


def test_unittest_aliases() -> None:
    out = fix("self.assertEquals(a, b)\nself.assertItemsEqual(a, b)\nself.failUnless(x)\n")
    assert out == "self.assertEqual(a, b)\nself.assertCountEqual(a, b)\nself.assertTrue(x)\n"


def test_simple_renames() -> None:
    out = fix(
        "import base64, time, inspect, logging\n"
        "base64.encodestring(b'x')\ntime.clock()\ninspect.getargspec(f)\nlogging.warn('x')\n"
        "import xml.etree.cElementTree as ET\n"
    )
    assert "base64.encodebytes" in out
    assert "time.perf_counter()" in out
    assert "inspect.getfullargspec" in out
    assert "logging.warning(" in out
    assert "xml.etree.ElementTree as ET" in out


def test_dict_iter_and_xrange() -> None:
    out = fix("for k, v in d.iteritems():\n    for i in xrange(3):\n        pass\n")
    assert "d.items()" in out and "range(3)" in out


def test_backports() -> None:
    out = fix("import mock\nfrom mock import patch\nimport unittest2 as unittest\n")
    assert out == ("from unittest import mock\nfrom unittest.mock import patch\nimport unittest\n")


def test_imports_added_once() -> None:
    out = fix("import cgi\nimport fractions\ncgi.escape(s)\ncgi.escape(t)\nfractions.gcd(2, 4)\n")
    assert out.count("import html") == 1
    assert out.count("import math") == 1
    assert "html.escape(s)" in out and "math.gcd(2, 4)" in out


def test_yaml_load() -> None:
    assert "yaml.safe_load(f)" in fix("import yaml\nyaml.load(f)\n")
    assert "yaml.load(f, Loader=L)" in fix("import yaml\nyaml.load(f, Loader=L)\n")


def test_asyncio_coroutine() -> None:
    src = "import asyncio\n@asyncio.coroutine\ndef go():\n    yield from asyncio.sleep(1)\n"
    out = fix(src)
    assert "async def go():" in out and "await asyncio.sleep(1)" in out


def test_unparseable_input_is_returned_unchanged() -> None:
    src = 'print "x"\n'
    assert apply_api_fixes(src) == (src, [])


def test_ensure_import_respects_future_and_existing() -> None:
    src = "from __future__ import annotations\nimport os\n\nx = 1\n"
    out = ensure_import(src, "import html")
    assert out.splitlines()[:3] == [
        "from __future__ import annotations",
        "import os",
        "import html",
    ]
    assert ensure_import(out, "import html") == out


# Semantics check: the dict/xrange rewrites behave the same as the Python 2 meaning.
@given(st.dictionaries(st.text(max_size=5), st.integers(), max_size=10), st.integers(0, 50))
def test_rewritten_code_matches_python2_semantics(d: dict[str, int], n: int) -> None:
    py2 = (
        "def total(d, n):\n"
        "    s = 0\n"
        "    for k, v in d.iteritems():\n"
        "        s += v\n"
        "    for i in xrange(n):\n"
        "        s += i\n"
        "    return s, sorted(d.iterkeys()), sorted(d.itervalues())\n"
    )
    out = fix(py2)
    namespace: dict[str, object] = {}
    exec(compile(out, "<fixed>", "exec"), namespace)  # our own generated test code, not repo code
    expected = (sum(d.values()) + sum(range(n)), sorted(d), sorted(d.values()))
    assert namespace["total"](d, n) == expected  # type: ignore[operator]


def test_os_errno_gets_import() -> None:
    out = fix("import os\nif e.errno == os.errno.ENOENT:\n    pass\n")
    assert "errno.ENOENT" in out and "import errno" in out
