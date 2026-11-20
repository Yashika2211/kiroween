import pytest

from necromancer.cli import _print_event, main


def test_invalid_url_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["autopsy", "not a url"]) == 1
    assert "doesn't look like a GitHub repository" in capsys.readouterr().err


def test_print_event_formats(capsys: pytest.CaptureFixture[str]) -> None:
    _print_event("step", {"label": "Exhuming", "state": "done", "detail": "7 files"})
    _print_event("task", {"title": "Bump deps", "status": "failed", "note": "boom"})
    out = capsys.readouterr().out
    assert "✓ Exhuming (7 files)" in out and "✗ Bump deps  boom" in out
