from pathlib import Path

import pytest

from necromancer.autopsy.loc import count_code_lines, count_python_lines, enforce_limits
from necromancer.errors import NotAPythonRepo, RepoTooLarge


def test_count_code_lines_ignores_blank_and_comments() -> None:
    src = "# header\n\nimport os\n   # indented comment\nx = 1  # trailing\n"
    assert count_code_lines(src) == 2


def test_count_python_lines(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("a = 1\nb = 2\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("c = 3\n")
    (tmp_path / "README.md").write_text("not python\n")
    count = count_python_lines(tmp_path)
    assert count.files == 2
    assert count.lines == 3
    assert count.per_file["sub/c.py"] == 1


def test_enforce_limits_rejects_big_repos(tmp_path: Path) -> None:
    (tmp_path / "big.py").write_text("x = 1\n" * 11)
    with pytest.raises(RepoTooLarge, match="11 lines"):
        enforce_limits(count_python_lines(tmp_path), max_lines=10)


def test_enforce_limits_rejects_non_python(tmp_path: Path) -> None:
    with pytest.raises(NotAPythonRepo):
        enforce_limits(count_python_lines(tmp_path), max_lines=10)
