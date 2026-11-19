from necromancer.resurrection.diffing import make_diff, unified_diff


def test_make_diff_counts_lines() -> None:
    d = make_diff("m.py", "print 'x'\nx = 1\n", "print('x')\nx = 1\n", "py2to3")
    assert d is not None
    assert d.added == 1 and d.removed == 1
    assert d.diff.startswith("--- a/m.py\n+++ b/m.py\n")


def test_no_change_no_diff() -> None:
    assert make_diff("m.py", "x\n", "x\n", "api") is None


def test_missing_trailing_newline_is_marked() -> None:
    assert "\\ No newline at end of file" in unified_diff("m.py", "a", "b")
