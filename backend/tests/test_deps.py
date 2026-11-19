from pathlib import Path

from necromancer.autopsy.deps import (
    find_dependencies,
    find_dev_dependencies,
    parse_requirement,
    parse_setup_py,
)


def test_parse_requirement_variants() -> None:
    d = parse_requirement("numpy==1.8.1", "requirements.txt")
    assert d and d.pinned_version == "1.8.1" and d.minimum_version == "1.8.1"
    d = parse_requirement("Django>=1.4,<1.5  # old", "r.txt")
    assert d and d.canonical == "django" and d.pinned_version is None
    assert d.minimum_version == "1.4"
    d = parse_requirement("requests (>=2.0)", "setup.py")
    assert d and d.minimum_version == "2.0"
    d = parse_requirement("simplejson", "r.txt")
    assert d and d.spec == "" and d.pinned_version is None
    assert parse_requirement("# comment", "r.txt") is None
    assert parse_requirement("-e git+https://x/y.git#egg=y", "r.txt") is None
    assert parse_requirement("--index-url https://x", "r.txt") is None


def test_requirements_with_include(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("-r base.txt\nscipy==0.14.0\n")
    (tmp_path / "base.txt").write_text("numpy==1.8.1\n")
    names = {d.canonical: d for d in find_dependencies(tmp_path)}
    assert names["numpy"].pinned_version == "1.8.1"
    assert names["numpy"].source == "base.txt"
    assert names["scipy"].line == 2


def test_requirements_include_cannot_escape(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (tmp_path / "secret.txt").write_text("evil==1.0\n")
    (root / "requirements.txt").write_text("-r ../secret.txt\nok==1\n")
    assert [d.canonical for d in find_dependencies(root)] == ["ok"]


SETUP_PY2 = """
from setuptools import setup
REQS = ["ply>=3.4"]
print "building"
setup(
    name="x",
    install_requires=REQS + ['funktown>=0.4.6'],
)
"""


def test_setup_py_is_parsed_not_executed(tmp_path: Path) -> None:
    marker = tmp_path / "pwned"
    (tmp_path / "setup.py").write_text(
        f"open({str(marker)!r}, 'w').write('x')\n" + SETUP_PY2.replace('print "building"', "")
    )
    deps = parse_setup_py(tmp_path / "setup.py", tmp_path)
    assert {d.canonical for d in deps} == {"ply", "funktown"}
    assert not marker.exists()


def test_setup_py_with_python2_print(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text(SETUP_PY2)
    assert {d.canonical for d in parse_setup_py(tmp_path / "setup.py", tmp_path)} == {
        "ply",
        "funktown",
    }


def test_setup_cfg_and_pyproject(tmp_path: Path) -> None:
    (tmp_path / "setup.cfg").write_text("[options]\ninstall_requires =\n    arrow>=0.4\n    six\n")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["click==6.7"]\n'
        '[tool.poetry.dependencies]\npython = "^3.8"\nrequests = "^2.0"\n'
    )
    names = {d.canonical: d for d in find_dependencies(tmp_path)}
    assert set(names) == {"arrow", "six", "click", "requests"}
    assert names["click"].pinned_version == "6.7"
    assert names["requests"].minimum_version == "2.0"


def test_pinned_entry_wins_over_unpinned(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("arrow\n")
    (tmp_path / "setup.cfg").write_text("[options]\ninstall_requires =\n    arrow==0.4.2\n")
    (dep,) = find_dependencies(tmp_path)
    assert dep.pinned_version == "0.4.2"


def test_dev_requirements_are_separate(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("arrow\n")
    (tmp_path / "dev-requirements.txt").write_text("nose==1.3.0\nmock\n")
    assert [d.canonical for d in find_dependencies(tmp_path)] == ["arrow"]
    assert {d.canonical for d in find_dev_dependencies(tmp_path)} == {"nose", "mock"}


def test_nested_include_to_sibling_dir_is_allowed(tmp_path: Path) -> None:
    (tmp_path / "requirements").mkdir()
    (tmp_path / "requirements.txt").write_text("-r requirements/prod.txt\n")
    (tmp_path / "requirements" / "prod.txt").write_text("-r ../base.txt\n")
    (tmp_path / "base.txt").write_text("six==1.9.0\n")
    assert [d.canonical for d in find_dependencies(tmp_path)] == ["six"]
