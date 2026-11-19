from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from necromancer.resurrection.llm import (
    LLMFixer,
    LLMUnavailable,
    blame_file,
    build_prompt,
    extract_code,
)


class FakeStream:
    def __init__(self, message: Any) -> None:
        self.message = message

    async def get_final_message(self) -> Any:
        return self.message


class FakeClient:
    def __init__(self, text: str, stop_reason: str = "end_turn") -> None:
        self.calls: list[dict[str, Any]] = []
        message = SimpleNamespace(
            stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)]
        )

        @asynccontextmanager
        async def stream(**kwargs: Any):
            self.calls.append(kwargs)
            yield FakeStream(message)

        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=stream))


def test_extract_code() -> None:
    code, why = extract_code("```python\nx = 1\n```\nFixed the import.\n")
    assert code == "x = 1\n" and why == "Fixed the import."
    assert extract_code("no code here") == (None, "")


def test_build_prompt_includes_file_failure_and_notes() -> None:
    prompt = build_prompt("a.py", "x = 1", "E   NameError", ["uses basestring"])
    assert "`a.py`" in prompt and "NameError" in prompt and "- uses basestring" in prompt


def test_requires_a_key() -> None:
    with pytest.raises(LLMUnavailable):
        LLMFixer(api_key=None)


async def test_fix_file_returns_parsed_fix_and_sends_one_file() -> None:
    client = FakeClient("```python\nimport collections.abc\n```\nUse collections.abc.")
    fixer = LLMFixer(api_key=None, client=client)  # type: ignore[arg-type]
    fix = await fixer.fix_file("m.py", "import collections\n", "E AttributeError")
    assert fix is not None
    assert fix.new_source == "import collections.abc\n"
    assert fix.explanation == "Use collections.abc."
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert len(call["messages"]) == 1


@pytest.mark.parametrize(
    ("text", "stop"),
    [
        ("```python\nprint 'still py2'\n```", "end_turn"),
        ("```python\nx = 1\n```", "refusal"),
        ("```python\nx = 1\n```", "max_tokens"),
        ("I can't help", "end_turn"),
        ("```python\nsame = 1\n```", "end_turn"),
    ],
)
async def test_unusable_replies_are_discarded(text: str, stop: str) -> None:
    fixer = LLMFixer(api_key=None, client=FakeClient(text, stop))  # type: ignore[arg-type]
    assert await fixer.fix_file("m.py", "same = 1\n", "E boom") is None


def test_blame_file_prefers_deepest_project_frame() -> None:
    output = (
        "tests/test_lisp.py:12: in test_eval\n"
        "    evaluate(x)\n"
        "pyclojure/core.py:88: in evaluate\n"
        "    return apply(f, args)\n"
        "E   NameError: name 'apply' is not defined\n"
    )
    files = {"tests/test_lisp.py", "pyclojure/core.py"}
    assert blame_file(output, files) == "pyclojure/core.py"
    assert blame_file("nothing", files) is None
