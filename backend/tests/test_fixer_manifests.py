from necromancer.models import Dependency, DependencyStatus, Severity, Vulnerability
from necromancer.resurrection.fixers.manifests import (
    plan_changes,
    rewrite_literal_requirements,
    rewrite_requirements,
    rewrite_setup_cfg,
)

DEPS = [
    Dependency(
        name="numpy",
        spec="==1.8.1",
        pinned_version="1.8.1",
        source="r",
        latest="2.1.0",
        status=DependencyStatus.OUTDATED,
    ),
    Dependency(
        name="requests",
        spec=">=2.0",
        pinned_version="2.0",
        source="r",
        latest="2.32.3",
        status=DependencyStatus.OUTDATED,
    ),
    Dependency(
        name="nose", spec="==1.3.0", source="r", status=DependencyStatus.DEAD, replacement="pytest"
    ),
    Dependency(name="argparse", spec="", source="r", status=DependencyStatus.DEAD),
    Dependency(
        name="six",
        spec="==1.16.0",
        pinned_version="1.16.0",
        source="r",
        latest="1.16.0",
        status=DependencyStatus.OK,
    ),
    Dependency(name="arrow", spec="", source="r", latest="1.3.0", status=DependencyStatus.UNPINNED),
]
VULNS = [
    Vulnerability(id="X", package="six", version="1.16.0", severity=Severity.HIGH, fixed="1.17.0")
]


def test_plan_changes() -> None:
    changes = plan_changes(DEPS, VULNS)
    assert changes["numpy"].new_requirement == "numpy==2.1.0"
    assert changes["requests"].new_requirement == "requests>=2.32.3"
    assert changes["nose"].new_requirement == "pytest"
    assert changes["argparse"].new_requirement is None
    assert changes["six"].new_requirement == "six>=1.17.0"
    assert "arrow" not in changes


def test_vuln_fix_above_latest_wins() -> None:
    deps = [
        Dependency(
            name="pkg",
            spec="==1.0",
            pinned_version="1.0",
            source="r",
            latest="1.5",
            status=DependencyStatus.OUTDATED,
        )
    ]
    vulns = [Vulnerability(id="V", package="pkg", fixed="1.6")]
    assert plan_changes(deps, vulns)["pkg"].new_requirement == "pkg==1.6"


def test_rewrite_requirements_preserves_layout() -> None:
    text = (
        "# runtime\n"
        "numpy==1.8.1  # math\n"
        "nose==1.3.0\n"
        "argparse\n"
        "-e git+https://example.com/x.git#egg=x\n"
        "arrow\n"
        "requests[security]>=2.0; python_version >= '3'\n"
    )
    out, notes = rewrite_requirements(text, plan_changes(DEPS, VULNS))
    assert out.splitlines() == [
        "# runtime",
        "numpy==2.1.0  # math",
        "pytest",
        "# argparse  # removed by Necromancer: argparse is now part of the standard library",
        "-e git+https://example.com/x.git#egg=x",
        "arrow",
        'requests[security]>=2.32.3; python_version >= "3"',
    ]
    assert len(notes) == 4


def test_rewrite_setup_py_literals() -> None:
    src = (
        "setup(\n"
        "    install_requires=[\n"
        "        'numpy==1.8.1',\n"
        "        'argparse',\n"
        "        'arrow',\n"
        "    ],\n"
        "    name='numpy-tools',\n"
        ")\n"
    )
    out, notes = rewrite_literal_requirements(src, plan_changes(DEPS, VULNS))
    assert "'numpy==2.1.0'" in out
    assert "argparse" not in out
    assert "'arrow'" in out
    assert "name='numpy-tools'" in out
    compile(out, "setup.py", "exec")
    assert len(notes) == 2


def test_rewrite_inline_list() -> None:
    out, _ = rewrite_literal_requirements(
        "deps = ['six==1.16.0', 'argparse']\n", plan_changes(DEPS, VULNS)
    )
    assert out == "deps = ['six>=1.17.0']\n"


def test_rewrite_setup_cfg() -> None:
    src = "[options]\ninstall_requires =\n    numpy==1.8.1\n    argparse\n    arrow\n[other]\nkey = numpy==1.8.1\n"
    out, notes = rewrite_setup_cfg(src, plan_changes(DEPS, VULNS))
    assert (
        out
        == "[options]\ninstall_requires =\n    numpy==2.1.0\n    arrow\n[other]\nkey = numpy==1.8.1\n"
    )
    assert len(notes) == 2
