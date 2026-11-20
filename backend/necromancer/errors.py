"""Typed exceptions. Anything raised from here is safe to show to a user."""

from __future__ import annotations


class NecromancerError(Exception):
    """Base class for user-facing errors."""

    code: str = "necromancer_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidRepoURL(NecromancerError):
    code = "invalid_repo_url"


class CloneFailed(NecromancerError):
    code = "clone_failed"


class RepoTooLarge(NecromancerError):
    code = "repo_too_large"


class NotAPythonRepo(NecromancerError):
    code = "not_a_python_repo"


class UnsafePath(NecromancerError):
    code = "unsafe_path"


class JobNotFound(NecromancerError):
    code = "job_not_found"


class InvalidJobState(NecromancerError):
    code = "invalid_job_state"


class RateLimited(NecromancerError):
    code = "rate_limited"
