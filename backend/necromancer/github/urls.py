"""Parse and normalise GitHub repository URLs."""

from __future__ import annotations

import re
from dataclasses import dataclass

from necromancer.errors import InvalidRepoURL

_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})"
_REPO = r"[A-Za-z0-9._-]{1,100}"

_PATTERNS = [
    re.compile(
        rf"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>{_NAME})/(?P<repo>{_REPO}?)"
        r"(?:\.git)?(?:/(?:tree|blob)/[^\s]*)?/?(?:[?#].*)?$"
    ),
    re.compile(rf"^git@github\.com:(?P<owner>{_NAME})/(?P<repo>{_REPO}?)(?:\.git)?$"),
    re.compile(rf"^(?P<owner>{_NAME})/(?P<repo>{_REPO}?)$"),
]


@dataclass(frozen=True)
class RepoRef:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def html_url(self) -> str:
        return f"https://github.com/{self.full_name}"

    @property
    def clone_url(self) -> str:
        return f"{self.html_url}.git"


def parse_repo_url(raw: str) -> RepoRef:
    """Return the owner/name for a GitHub URL, `git@` remote or `owner/repo` shorthand."""
    text = (raw or "").strip()
    if not text:
        raise InvalidRepoURL("Paste a GitHub repository URL, like https://github.com/owner/repo.")
    for pattern in _PATTERNS:
        match = pattern.match(text)
        if match:
            owner, name = match.group("owner"), match.group("repo")
            if name.endswith(".git"):
                name = name[:-4]
            if name in {"", ".", ".."}:
                break
            return RepoRef(owner=owner, name=name)
    raise InvalidRepoURL(
        f"{text!r} doesn't look like a GitHub repository. "
        "Use the form https://github.com/owner/repo."
    )
