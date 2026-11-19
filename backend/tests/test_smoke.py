import subprocess
import sys
from pathlib import Path

from necromancer.resurrection.smoke import (
    discover_modules,
    find_pure_functions,
    generate_tests,
    render_smoke_tests,
)


def write(root: Path, rel: str, text: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_discover_modules(tmp_path: Path) -> None:
    write(tmp_path, "pkg/__init__.py")
    write(tmp_path, "pkg/core.py")
    write(tmp_path, "pkg/sub/__init__.py")
    write(tmp_path, "pkg/sub/deep.py")
    write(tmp_path, "pkg/nosub/orphan.py")  # no __init__ → not importable as pkg.nosub
    write(tmp_path, "pkg/test_core.py")
    write(tmp_path, "tests/test_x.py")
    write(tmp_path, "setup.py")
    write(tmp_path, "single.py")
    write(tmp_path, "bad-name.py")
    write(tmp_path, "docs/conf.py")
    assert discover_modules(tmp_path) == ["pkg", "pkg.core", "pkg.sub", "pkg.sub.deep", "single"]


def test_src_layout(tmp_path: Path) -> None:
    write(tmp_path, "src/lib/__init__.py")
    write(tmp_path, "src/lib/a.py")
    assert discover_modules(tmp_path) == ["lib", "lib.a"]


def test_smoke_file_is_valid_python() -> None:
    compile(render_smoke_tests(["a", "b.c"]), "t.py", "exec")


def test_find_pure_functions() -> None:
    src = (
        "def add(a=0, b=0):\n    return a + b\n"
        "def typed(x: int, y: str):\n    return str(x) + y\n"
        "def noisy(a=1):\n    print(a)\n"
        "def unknown(a):\n    return a\n"
        "def _private(a=1):\n    return a\n"
        "def uses_os(p=''):\n    return os.path.exists(p)\n"
    )
    names = [f.name for f in find_pure_functions(src, "m")]
    assert names == ["add", "typed"]


def test_generated_property_tests_run_and_pass(tmp_path: Path) -> None:
    before, after = tmp_path / "before", tmp_path / "after"
    for root, body in (
        (before, "def scale(x=1, factor=2):\n    return x * factor\n"),
        (after, "def scale(x: int = 1, factor: int = 2) -> int:\n    return x * factor\n"),
    ):
        write(root, "mathy/__init__.py")
        write(root, "mathy/ops.py", body)
    generated = generate_tests(before, after)
    assert [f.name for f in generated.properties] == ["scale"]
    for rel, content in generated.files.items():
        write(after, rel, content)
    # This runs our *generated* test file against a toy package we wrote above (not repo code).
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        cwd=after,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(after), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "passed" in result.stdout


def test_property_test_catches_behaviour_change(tmp_path: Path) -> None:
    before, after = tmp_path / "before", tmp_path / "after"
    write(before, "m.py", "def f(x=1):\n    return x // 2\n")
    write(after, "m.py", "def f(x=1):\n    return x / 2\n")
    for rel, content in generate_tests(before, after).files.items():
        write(after, rel, content)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        cwd=after,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(after), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 1
    assert "matches_original" in result.stdout
