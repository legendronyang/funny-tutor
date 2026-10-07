"""Tests for the provider-independent LLM client."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.llm_client import (
    LLMClient,
    LLMConfig,
    LLMResponseError,
    decide_field_mode,
    load_llm_config,
    load_system_prompt,
    parse_json_response,
)


def test_parse_json_response_accepts_common_wrappers() -> None:
    cases = [
        ('{"funny_explanation":"hello"}', {"funny_explanation": "hello"}),
        ("```json\n{\"memory_aids\":[\"A\",\"B\"]}\n```", {"memory_aids": ["A", "B"]}),
        ('模型回答如下：\\n{"common_misconceptions":["只看B不看方向"]}\\n以上。', {"common_misconceptions": ["只看B不看方向"]}),
    ]
    for raw, expected in cases:
        assert parse_json_response(raw, "em-001") == expected


def test_parse_json_response_rejects_invalid_content_with_question_id() -> None:
    with pytest.raises(LLMResponseError, match="em-001"):
        parse_json_response("not json at all", "em-001")


def test_parse_json_response_rejects_empty_content_with_question_id() -> None:
    with pytest.raises(LLMResponseError, match="em-002"):
        parse_json_response("", "em-002")


@pytest.mark.parametrize("value, expected", [
    (None, "generate"), ("", "generate"), ("   ", "generate"),
    ([], "generate"), ({}, "generate"), ("B", "verify"),
    (["B"], "verify"), ({"answer": "B"}, "verify"),
])
def test_decide_field_mode(value: object, expected: str) -> None:
    assert decide_field_mode(value) == expected


def test_load_llm_config_reads_local_ollama_config() -> None:
    config = load_llm_config(Path("config.toml"))
    assert config.model == "ollama/qwen3.5:9b"
    assert config.api_base == "http://localhost:11434"
    assert config.api_key_env is None


def test_load_system_prompt_contains_hard_constraints() -> None:
    prompt = load_system_prompt(Path("src/prompts/funny_tutor_em.txt"))
    assert "绝不改写输入中的 LaTeX" in prompt
    assert "独立求解后再验证" in prompt
    assert "一个合法 JSON 对象" in prompt


def test_complete_json_uses_configured_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content='{"ok":true}')
            )]
        )

    import src.llm_client as module
    monkeypatch.setattr(module.litellm, "completion", fake_completion)

    client = LLMClient(
        LLMConfig(model="ollama/qwen3.5:9b", api_base="http://localhost:11434"),
        "SYSTEM",
    )
    result = client.complete_json(
        question_id="em-001",
        user_prompt="Do the task.",
        mode="verify",
    )

    assert result == {"ok": True}
    assert captured["model"] == "ollama/qwen3.5:9b"
    assert captured["api_base"] == "http://localhost:11434"
    assert captured["messages"][0]["role"] == "system"
    assert "MODE: VERIFY" in captured["messages"][1]["content"]
