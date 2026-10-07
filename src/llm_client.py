"""LLM client contracts and response parsing for Funny Tutor.

The first implementation slice keeps provider/network concerns out of the
parsing logic so the JSON contract can be verified independently.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

GenerationMode = Literal["generate", "verify"]


class LLMResponseError(ValueError):
    """Raised when an LLM response cannot be parsed as the expected JSON."""

    def __init__(self, question_id: str, reason: str) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id}: {reason}")


def decide_field_mode(value: Any) -> GenerationMode:
    """Return whether a canonical field needs generation or verification.

    Empty values are generated. Existing non-empty values are verified
    independently by the caller; the provided value must not become the model's
    reasoning conclusion.
    """

    if value is None:
        return "generate"
    if isinstance(value, str) and not value.strip():
        return "generate"
    if isinstance(value, (list, tuple, dict)) and not value:
        return "generate"
    return "verify"


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    return fenced.group(1).strip() if fenced else text


def parse_json_response(raw_text: str, question_id: str) -> dict[str, Any]:
    """Extract and parse the first JSON object from an LLM response.

    Accepts plain JSON, a fenced JSON block, or brief prose surrounding a JSON
    object. Raises LLMResponseError with the question id on failure.
    """

    if not raw_text or not raw_text.strip():
        raise LLMResponseError(question_id, "LLM returned empty content")

    candidate = _strip_code_fence(raw_text)

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", candidate):
        try:
            value, _ = decoder.raw_decode(candidate[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value

    raise LLMResponseError(
        question_id,
        "unable to extract a valid JSON object from LLM response",
    )
