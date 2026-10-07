"""Tests for the provider-independent LLM response contract."""

from __future__ import annotations

import pytest

from src.llm_client import LLMResponseError, decide_field_mode, parse_json_response


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"funny_explanation":"hello"}', {"funny_explanation": "hello"}),
        (
            "```json\n{\"memory_aids\":[\"A\",\"B\"]}\n```",
            {"memory_aids": ["A", "B"]},
        ),
        (
            '模型回答如下：\\n{"common_misconceptions":["只看B不看方向"]}\\n以上。',
            {"common_misconceptions": ["只看B不看方向"]},
        ),
    ],
)
def test_parse_json_response_accepts_common_wrappers(
    raw: str, expected: dict
) -> None:
    assert parse_json_response(raw, "em-001") == expected


def test_parse_json_response_rejects_invalid_content_with_question_id() -> None:
    with pytest.raises(LLMResponseError, match="em-001"):
        parse_json_response("not json at all", "em-001")


def test_parse_json_response_rejects_empty_content_with_question_id() -> None:
    with pytest.raises(LLMResponseError, match="em-002"):
        parse_json_response("", "em-002")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "generate"),
        ("", "generate"),
        ("   ", "generate"),
        ([], "generate"),
        ({}, "generate"),
        ("B", "verify"),
        (["B"], "verify"),
        ({"answer": "B"}, "verify"),
    ],
)
def test_decide_field_mode(value: object, expected: str) -> None:
    assert decide_field_mode(value) == expected
