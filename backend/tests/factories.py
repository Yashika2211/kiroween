"""Builders for model objects used across tests."""

from datetime import UTC, datetime

from necromancer.models import (
    DeathCertificate,
    Dependency,
    DependencyStatus,
    FileHealth,
    Marker,
    MarkerCategory,
    Severity,
    VitalRecords,
    Vulnerability,
)


def certificate(**overrides: object) -> DeathCertificate:
    base: dict[str, object] = dict(
        vitals=VitalRecords(
            full_name="someone/deadrepo",
            url="https://github.com/someone/deadrepo",
            created_at=datetime(2011, 1, 1, tzinfo=UTC),
            last_commit_at=datetime(2013, 3, 12, tzinfo=UTC),
            archived=True,
            default_branch="master",
        ),
        python_lines=120,
        python_files=3,
        files=[
            FileHealth(path="deadrepo/core.py", lines=20, parses=False, error="invalid syntax"),
            FileHealth(path="deadrepo/__init__.py", lines=0, parses=True),
            FileHealth(path="tests/test_core.py", lines=10, parses=True),
        ],
        markers=[
            Marker(
                file="deadrepo/core.py",
                line=14,
                kind="print_statement",
                category=MarkerCategory.SYNTAX,
                excerpt='print "x"',
            ),
            Marker(
                file="deadrepo/core.py",
                line=7,
                kind="dict_iteritems",
                category=MarkerCategory.BUILTIN,
                excerpt="d.iteritems()",
            ),
            Marker(
                file="deadrepo/core.py",
                line=1,
                kind="removed_module",
                category=MarkerCategory.STDLIB,
                excerpt="import urllib2",
            ),
            Marker(
                file="tests/test_core.py",
                line=8,
                kind="unittest_aliases",
                category=MarkerCategory.API,
                excerpt="self.assertEquals",
            ),
        ],
        has_tests=True,
        dependencies=[
            Dependency(
                name="requests",
                pinned_version="2.2.1",
                source="requirements.txt",
                latest="2.32.3",
                status=DependencyStatus.OUTDATED,
            ),
            Dependency(
                name="nose",
                pinned_version="1.3.0",
                source="requirements.txt",
                status=DependencyStatus.DEAD,
                replacement="pytest",
            ),
        ],
        vulnerabilities=[
            Vulnerability(
                id="GHSA-x",
                package="requests",
                version="2.2.1",
                severity=Severity.HIGH,
                fixed="2.3.0",
            )
        ],
        decay_score=78,
        decay_label="Skeletal",
        cause_of_death="Acute Python 2 syndrome: 1 file fails to parse on Python 3.12 (print statement).",
    )
    base.update(overrides)
    return DeathCertificate(**base)  # type: ignore[arg-type]
