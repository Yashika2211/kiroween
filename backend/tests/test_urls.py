import pytest
from hypothesis import given
from hypothesis import strategies as st

from necromancer.errors import InvalidRepoURL
from necromancer.github.urls import parse_repo_url


@pytest.mark.parametrize(
    "raw",
    [
        "https://github.com/nvie/times",
        "https://github.com/nvie/times/",
        "https://github.com/nvie/times.git",
        "http://www.github.com/nvie/times",
        "github.com/nvie/times",
        "https://github.com/nvie/times/tree/master/times",
        "https://github.com/nvie/times/blob/master/setup.py",
        "https://github.com/nvie/times?tab=readme",
        "git@github.com:nvie/times.git",
        "nvie/times",
        "  https://github.com/nvie/times  ",
    ],
)
def test_parses_common_forms(raw: str) -> None:
    ref = parse_repo_url(raw)
    assert ref.full_name == "nvie/times"
    assert ref.clone_url == "https://github.com/nvie/times.git"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "https://gitlab.com/nvie/times",
        "https://github.com/nvie",
        "https://github.com/nvie/../etc",
        "not a url",
        "https://github.com/-bad/name",
        "https://github.com/nvie/times; rm -rf /",
    ],
)
def test_rejects_bad_input(raw: str) -> None:
    with pytest.raises(InvalidRepoURL):
        parse_repo_url(raw)


def test_keeps_dots_in_repo_names() -> None:
    assert parse_repo_url("https://github.com/owner/my.repo").name == "my.repo"


@given(st.text(max_size=200))
def test_never_crashes_and_never_yields_path_traversal(raw: str) -> None:
    try:
        ref = parse_repo_url(raw)
    except InvalidRepoURL:
        return
    assert "/" not in ref.name
    assert ref.name not in {".", ".."}
    assert " " not in ref.full_name
