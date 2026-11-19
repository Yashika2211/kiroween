"""PyPI lookups and the table of dead / superseded packages."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from necromancer.autopsy.deps import DeclaredDependency
from necromancer.models import Dependency, DependencyStatus

PYPI = "https://pypi.org/pypi"
TARGET_PYTHON = Version("3.12")

# canonical name -> (replacement or None if now in the stdlib, explanation)
DEAD_PACKAGES: dict[str, tuple[str | None, str]] = {
    "pycrypto": ("pycryptodome", "unmaintained since 2013, known CVEs"),
    "pil": ("pillow", "PIL was replaced by the Pillow fork"),
    "mysql-python": ("mysqlclient", "no Python 3 support"),
    "distribute": ("setuptools", "merged back into setuptools"),
    "beautifulsoup": ("beautifulsoup4", "BeautifulSoup 3 is Python 2 only"),
    "pep8": ("pycodestyle", "renamed"),
    "sklearn": ("scikit-learn", "the sklearn alias package is deprecated"),
    "nose": ("pytest", "nose is unmaintained and broken on Python 3.10+"),
    "unittest2": (None, "backport of the standard library unittest"),
    "mock": (None, "use unittest.mock from the standard library"),
    "argparse": (None, "in the standard library since 2.7"),
    "enum34": (None, "enum is in the standard library"),
    "futures": (None, "concurrent.futures is in the standard library"),
    "ordereddict": (None, "collections.OrderedDict is in the standard library"),
    "importlib": (None, "in the standard library"),
    "wsgiref": (None, "in the standard library"),
    "typing": (None, "in the standard library"),
    "dataclasses": (None, "in the standard library since 3.7"),
    "pathlib": (None, "in the standard library"),
    "subprocess32": (None, "backport of subprocess"),
    "trollius": (None, "use asyncio"),
    "oauth2": ("oauthlib", "abandoned"),
    "python-openid": ("python3-openid", "Python 2 only"),
    "django-nose": ("pytest-django", "depends on nose"),
    "pyandoc": ("pypandoc", "abandoned"),
}


@dataclass(frozen=True)
class PackageInfo:
    name: str
    latest: str | None
    compatible: str | None
    exists: bool


def _supports_target(requires_python: str | None) -> bool:
    if not requires_python:
        return True
    try:
        return TARGET_PYTHON in SpecifierSet(requires_python)
    except InvalidSpecifier:
        return True


def pick_compatible(data: dict) -> str | None:
    """Newest non-yanked, non-prerelease version whose files allow Python 3.12."""
    releases: dict[str, list[dict]] = data.get("releases") or {}
    candidates: list[Version] = []
    for raw, files in releases.items():
        try:
            version = Version(raw)
        except InvalidVersion:
            continue
        if version.is_prerelease or not files:
            continue
        if all(f.get("yanked") for f in files):
            continue
        if any(_supports_target(f.get("requires_python")) for f in files):
            candidates.append(version)
    if candidates:
        return str(max(candidates))
    latest = (data.get("info") or {}).get("version")
    return str(latest) if latest else None


async def fetch_package(client: httpx.AsyncClient, name: str) -> PackageInfo:
    response = await client.get(f"{PYPI}/{name}/json")
    if response.status_code == 404:
        return PackageInfo(name=name, latest=None, compatible=None, exists=False)
    response.raise_for_status()
    data = response.json()
    latest = (data.get("info") or {}).get("version")
    return PackageInfo(name=name, latest=latest, compatible=pick_compatible(data), exists=True)


def classify(dep: DeclaredDependency, info: PackageInfo | None) -> Dependency:
    result = Dependency(
        name=dep.name,
        spec=dep.spec,
        pinned_version=dep.pinned_version or dep.minimum_version,
        source=dep.source,
    )
    if dep.canonical in DEAD_PACKAGES:
        replacement, note = DEAD_PACKAGES[dep.canonical]
        result.status = DependencyStatus.DEAD
        result.replacement = replacement
        result.note = note
        result.latest = info.compatible if info else None
        return result
    if info is None:
        result.status = DependencyStatus.UNKNOWN
        result.note = "PyPI lookup failed"
        return result
    if not info.exists:
        result.status = DependencyStatus.MISSING
        result.note = "not found on PyPI"
        return result
    result.latest = info.compatible or info.latest
    current = dep.pinned_version or dep.minimum_version
    if not current:
        result.status = DependencyStatus.UNPINNED
        result.note = "no version constraint"
        return result
    try:
        behind = result.latest is not None and Version(current) < Version(result.latest)
    except InvalidVersion:
        behind = False
    if behind:
        result.status = DependencyStatus.OUTDATED
        result.note = f"{current} → {result.latest}"
    else:
        result.status = DependencyStatus.OK
    return result


async def check_dependencies(
    deps: list[DeclaredDependency],
    *,
    client: httpx.AsyncClient | None = None,
    concurrency: int = 8,
) -> tuple[list[Dependency], list[str]]:
    """Look up every dependency on PyPI concurrently. Returns (dependencies, warnings)."""
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=8.0, headers={"User-Agent": "necromancer"})
    semaphore = asyncio.Semaphore(concurrency)
    warnings: list[str] = []

    async def one(dep: DeclaredDependency) -> Dependency:
        async with semaphore:
            try:
                info = await fetch_package(http, dep.canonical)
            except (httpx.HTTPError, ValueError) as exc:
                warnings.append(f"PyPI lookup failed for {dep.name}: {type(exc).__name__}")
                info = None
        return classify(dep, info)

    try:
        results = await asyncio.gather(*(one(d) for d in deps))
    finally:
        if own_client:
            await http.aclose()
    return list(results), warnings
