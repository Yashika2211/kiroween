from necromancer.resurrection.fixers.modernize import pyupgrade


def test_pyupgrade_modernises() -> None:
    src = (
        "# -*- coding: utf-8 -*-\n"
        "from __future__ import print_function\n"
        "class A(object):\n"
        "    def f(self):\n"
        "        return super(A, self).f(), u'x', set([1, 2]), '%s' % 'y'\n"
    )
    out = pyupgrade(src)
    assert "class A:" in out
    assert "super().f()" in out
    assert "u'x'" not in out
    assert "{1, 2}" in out
    assert "__future__" not in out
    assert "coding" not in out


def test_pyupgrade_leaves_python2_alone() -> None:
    src = 'print "x"\n'
    assert pyupgrade(src) == src


def test_pyupgrade_is_idempotent() -> None:
    once = pyupgrade("class A(object):\n    pass\n")
    assert pyupgrade(once) == once
