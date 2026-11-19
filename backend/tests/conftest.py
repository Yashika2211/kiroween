import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def dead_repo(tmp_path: Path) -> Path:
    """A copy of the small Python 2 fixture repository."""
    dest = tmp_path / "deadrepo"
    shutil.copytree(FIXTURES / "deadrepo", dest)
    return dest
