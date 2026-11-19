import httpx
import respx

from necromancer.autopsy.deps import parse_requirement
from necromancer.autopsy.pypi import (
    PYPI,
    PackageInfo,
    check_dependencies,
    classify,
    pick_compatible,
)
from necromancer.models import DependencyStatus


def dep(text: str):
    d = parse_requirement(text, "requirements.txt")
    assert d is not None
    return d


def test_pick_compatible_skips_prerelease_yanked_and_py2_only() -> None:
    data = {
        "info": {"version": "3.0b1"},
        "releases": {
            "1.0": [{"requires_python": None}],
            "2.0": [{"requires_python": ">=3.8"}],
            "2.1": [{"requires_python": ">=3.13"}],
            "2.2": [{"requires_python": None, "yanked": True}],
            "3.0b1": [{"requires_python": None}],
            "junk": [{}],
            "0.9": [],
        },
    }
    assert pick_compatible(data) == "2.0"


def test_classify_outdated_ok_unpinned_missing_dead() -> None:
    fresh = PackageInfo("numpy", latest="2.1.0", compatible="2.1.0", exists=True)
    assert classify(dep("numpy==1.8.1"), fresh).status is DependencyStatus.OUTDATED
    assert classify(dep("numpy==2.1.0"), fresh).status is DependencyStatus.OK
    assert classify(dep("numpy"), fresh).status is DependencyStatus.UNPINNED
    gone = PackageInfo("funktown", latest=None, compatible=None, exists=False)
    assert classify(dep("funktown>=0.4"), gone).status is DependencyStatus.MISSING
    dead = classify(dep("pycrypto==2.6"), None)
    assert dead.status is DependencyStatus.DEAD and dead.replacement == "pycryptodome"
    stdlib = classify(dep("argparse"), None)
    assert stdlib.status is DependencyStatus.DEAD and stdlib.replacement is None
    assert classify(dep("arrow"), None).status is DependencyStatus.UNKNOWN


@respx.mock
async def test_check_dependencies_queries_pypi_concurrently() -> None:
    respx.get(f"{PYPI}/numpy/json").respond(
        json={"info": {"version": "2.1.0"}, "releases": {"2.1.0": [{"requires_python": ">=3.10"}]}}
    )
    respx.get(f"{PYPI}/nopkg/json").respond(status_code=404)
    respx.get(f"{PYPI}/flaky/json").mock(side_effect=httpx.ConnectError("boom"))
    results, warnings = await check_dependencies([dep("numpy==1.8.1"), dep("nopkg"), dep("flaky")])
    by_name = {r.name: r for r in results}
    assert by_name["numpy"].status is DependencyStatus.OUTDATED
    assert by_name["numpy"].latest == "2.1.0"
    assert by_name["nopkg"].status is DependencyStatus.MISSING
    assert by_name["flaky"].status is DependencyStatus.UNKNOWN
    assert any("flaky" in w for w in warnings)
