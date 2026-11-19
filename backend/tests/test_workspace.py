from pathlib import Path

import pytest

from necromancer.errors import UnsafePath
from necromancer.workspace import Workspace, iter_python_files, read_text, safe_join


def test_safe_join_allows_children(tmp_path: Path) -> None:
    assert safe_join(tmp_path, "a/b.py") == (tmp_path / "a" / "b.py").resolve()


@pytest.mark.parametrize("bad", ["../x", "a/../../x", "/etc/passwd"])
def test_safe_join_blocks_escape(tmp_path: Path, bad: str) -> None:
    with pytest.raises(UnsafePath):
        safe_join(tmp_path, bad)


def test_iter_python_files_skips_vendored_and_symlinks(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n")
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "b.py").write_text("x = 1\n")
    outside = tmp_path.parent / "outside_secret.py"
    outside.write_text("secret = 1\n")
    (tmp_path / "pkg" / "link.py").symlink_to(outside)
    files = [p.relative_to(tmp_path).as_posix() for p in iter_python_files(tmp_path)]
    assert files == ["pkg/a.py"]


def test_read_text_handles_latin1(tmp_path: Path) -> None:
    f = tmp_path / "old.py"
    f.write_bytes("# caf\xe9\n".encode("latin-1"))
    assert "caf" in read_text(f)


def test_workspace_rejects_weird_job_ids(tmp_path: Path) -> None:
    with pytest.raises(UnsafePath):
        Workspace.for_job(tmp_path, "../evil")


def test_fork_working_copy(tmp_path: Path) -> None:
    ws = Workspace.for_job(tmp_path, "abc123")
    ws.prepare()
    ws.before.mkdir()
    (ws.before / "m.py").write_text("print 1\n")
    after = ws.fork_working_copy()
    assert (after / "m.py").read_text() == "print 1\n"
    ws.destroy()
    assert not ws.root.exists()
