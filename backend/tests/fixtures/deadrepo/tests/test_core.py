import unittest

from deadrepo.core import shout, total


class CoreTest(unittest.TestCase):
    def test_total(self):
        self.assertEquals(total({"a": 1, "b": 2}), 3)

    def test_shout(self):
        self.assertEquals(shout("hi"), "HI")
