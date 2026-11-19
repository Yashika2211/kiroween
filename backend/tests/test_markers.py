from pathlib import Path

import pytest

from necromancer.autopsy.markers import (
    blank_strings_and_comments,
    check_parses,
    scan_repo,
    scan_source,
)

PY2 = """\
import urllib2
from urlparse import urljoin
from collections import Mapping
import ConfigParser

def greet(name):
    print "hello %s" % name
    print >>sys.stderr, "warn"
    print

def risky():
    try:
        pass
    except ValueError, e:
        raise TypeError, "bad"
    if 1 <> 2:
        x = `e`
    mode = 0755
    big = 10L
    s = ur"raw"
    exec "x = 1"

for k, v in d.iteritems():
    if d.has_key(k) and isinstance(v, basestring):
        for i in xrange(3):
            print unicode(v)
answer = raw_input("? ")
"""

PY3 = """\
from __future__ import unicode_literals
import collections.abc

def ok(items: dict[str, int]) -> None:
    print("print statement inside a string: print 'x'")
    # print "commented out" and xrange( in a comment
    for k, v in items.items():
        print(k, v, sep="")
    x = 0o755
    y = 0
    z = 1.0e10
"""


def kinds(source: str) -> set[str]:
    return {m.kind for m in scan_source(source, "m.py")}


def test_detects_python2_markers() -> None:
    found = kinds(PY2)
    expected = {
        "removed_module",
        "collections_abc_import",
        "print_statement",
        "except_comma",
        "raise_comma",
        "ne_operator",
        "backticks",
        "octal_literal",
        "long_suffix",
        "ur_prefix",
        "exec_statement",
        "dict_iteritems",
        "dict_has_key",
        "basestring",
        "xrange",
        "unicode",
        "raw_input",
    }
    assert expected <= found, expected - found


def test_python3_code_is_clean() -> None:
    assert kinds(PY3) == set()


def test_markers_carry_location_and_hint() -> None:
    markers = scan_source(PY2, "pkg/old.py")
    first_print = next(m for m in markers if m.kind == "print_statement")
    assert first_print.file == "pkg/old.py"
    assert first_print.line == 7
    assert first_print.excerpt.startswith('print "hello')
    assert "function" in first_print.hint


@pytest.mark.parametrize(
    "line",
    ["print = 3", "print(x)", "print (x)", "printer = 1", "self.print_x()", "print.__doc__"],
)
def test_print_false_positives(line: str) -> None:
    assert "print_statement" not in kinds(line)


def test_blanking_keeps_line_count_and_handles_triple_quotes() -> None:
    src = 'a = """\nprint "x"\n"""\nb = 1  # print "y"\n'
    lines = blank_strings_and_comments(src)
    assert len(lines) == 4
    assert "print" not in lines[1]
    assert lines[3].rstrip() == "b = 1"


def test_blanking_handles_escaped_quotes() -> None:
    lines = blank_strings_and_comments('s = "a \\" xrange(" + y\n')
    assert "xrange" not in lines[0]
    assert "+ y" in lines[0]


def test_check_parses() -> None:
    assert check_parses("x = 1\n") == (True, None)
    ok, err = check_parses('print "x"\n')
    assert not ok and err and "line 1" in err


def test_scan_repo_marks_unparseable_and_drops_syntax_fp(tmp_path: Path) -> None:
    (tmp_path / "old.py").write_text(PY2)
    # parses on py3 but contains "<>" inside an f-string format spec
    (tmp_path / "new.py").write_text('x = f"{1:<>10}"\n')
    scan = scan_repo(tmp_path)
    by_path = {f.path: f for f in scan.files}
    assert by_path["old.py"].parses is False
    assert by_path["new.py"].parses is True
    assert not [m for m in scan.markers if m.file == "new.py"]
    assert scan.counts["print_statement"] >= 3
    assert [f.path for f in scan.unparseable] == ["old.py"]
