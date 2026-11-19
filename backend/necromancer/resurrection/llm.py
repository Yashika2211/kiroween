"""LLM-assisted repair of a single file, using the Anthropic Messages API.

Only the one file being repaired, the failing test output and short guidance are sent.
The returned file is treated as untrusted text: it must parse as Python 3.12 before it is
written, and it is only ever executed inside the sandbox.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import anthropic

from necromancer.pyparse import parse_quietly

SYSTEM_PROMPT = """You repair abandoned Python projects so they run on Python 3.12.

You are given one source file from the project, the tail of a failing pytest run, and notes
from a static analysis. Return the complete corrected file.

Rules:
- Make the smallest change that fixes the failure and keeps behaviour the same.
- Target Python 3.12. Do not add new third-party dependencies.
- Keep the public API (names, signatures, return values) unchanged.
- Never weaken or delete tests to make them pass. Only change a test if it uses an API that
  no longer exists, and then keep what it checks.
- Reply with exactly one ```python fenced block containing the whole file, followed by one
  short sentence describing the change. No other text."""

MAX_FILE_CHARS = 60_000
_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)\n```", re.S)


@dataclass(frozen=True)
class LLMFix:
    path: str
    new_source: str
    explanation: str


class LLMUnavailable(Exception):
    pass


def extract_code(text: str) -> tuple[str | None, str]:
    """Return (code, explanation) from a reply containing one fenced Python block."""
    match = _FENCE.search(text)
    if not match:
        return None, ""
    code = match.group(1)
    explanation = text[match.end() :].strip().splitlines()
    return code + "\n", (explanation[0] if explanation else "")


def build_prompt(path: str, source: str, failure: str, notes: list[str]) -> str:
    joined = "\n".join(f"- {n}" for n in notes) or "- (none)"
    return (
        f"File: `{path}`\n\n"
        f"Static analysis notes:\n{joined}\n\n"
        f"Failing test output (tail):\n```\n{failure[-6000:]}\n```\n\n"
        f"Current contents of `{path}`:\n```python\n{source}\n```"
    )


class LLMFixer:
    def __init__(
        self,
        api_key: str | None,
        model: str = "claude-opus-5-5",
        *,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        if client is None and not api_key:
            raise LLMUnavailable("ANTHROPIC_API_KEY is not configured")
        self.model = model
        self.client = client or anthropic.AsyncAnthropic(api_key=api_key)

    async def fix_file(
        self, path: str, source: str, failure: str, notes: list[str] | None = None
    ) -> LLMFix | None:
        """Ask the model for a repaired file. Returns None when no usable fix comes back."""
        if len(source) > MAX_FILE_CHARS:
            return None
        try:
            async with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=64000,
                system=SYSTEM_PROMPT,
                output_config={"effort": "high"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                messages=[
                    {"role": "user", "content": build_prompt(path, source, failure, notes or [])}
                ],
            ) as stream:
                message = await stream.get_final_message()
        except anthropic.APIConnectionError:
            return None
        except anthropic.RateLimitError:
            return None
        except anthropic.APIStatusError:
            return None
        if message.stop_reason in ("refusal", "max_tokens"):
            return None
        text = "".join(b.text for b in message.content if b.type == "text")
        code, explanation = extract_code(text)
        if code is None or code == source:
            return None
        try:
            parse_quietly(code)
        except SyntaxError:
            return None
        return LLMFix(path=path, new_source=code, explanation=explanation)


_TRACE_FILE = re.compile(r'File "/tmp/run/([^"]+\.py)", line \d+')
_PYTEST_LOC = re.compile(r"^([\w/.-]+\.py):\d+: ", re.M)


def blame_file(output: str, candidates: set[str]) -> str | None:
    """Pick the repository file most likely responsible for a failure: the deepest
    traceback frame that is a project file, preferring non-test files."""
    frames = [m for m in _TRACE_FILE.findall(output) if m in candidates]
    frames += [m for m in _PYTEST_LOC.findall(output) if m in candidates]
    if not frames:
        return None
    non_test = [f for f in frames if "test" not in f.rsplit("/", 1)[-1]]
    return (non_test or frames)[-1]
