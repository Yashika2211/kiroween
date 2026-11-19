from necromancer.resurrection.fixers.missing import missing_modules, package_for

OUTPUT = """
ImportError while importing test module '/tmp/run/tests/test_times.py'.
E   ModuleNotFoundError: No module named 'pytz'
E   ModuleNotFoundError: No module named 'yaml.constructor'
E   ModuleNotFoundError: No module named 'pytz'
"""


def test_missing_modules_are_deduplicated_top_level() -> None:
    assert missing_modules(OUTPUT) == ["pytz", "yaml"]


def test_package_mapping() -> None:
    assert package_for("pytz", set()) == "pytz"
    assert package_for("yaml", set()) == "PyYAML"
    assert package_for("times", {"times"}) is None
    assert package_for("json", set()) is None
