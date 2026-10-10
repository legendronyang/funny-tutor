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
from src.schema import FunnyTutorPayload


def test_parse_json_response_accepts_common_wrappers() -> None:
    cases = [
        ('{"funny_explanation":"hello"}', {"funny_explanation": "hello"}),
        ('```json\n{\"memory_aids\":[\"A\",\"B\"]}\n```', {"memory_aids": ["A", "B"]}),
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


def test_load_llm_config_reads_local_ollama_chat_config() -> None:
    config = load_llm_config(Path("config.toml"))
    assert config.model == "ollama_chat/qwen3.5:9b-opencode"
    assert config.api_base == "http://localhost:11434"
    assert config.api_key_env is None
    assert config.timeout == 1800
    assert config.temperature == 0.0
    assert config.think_generate is False
    assert config.think_verify is True


def test_load_system_prompt_contains_hard_constraints() -> None:
    prompt = load_system_prompt(Path("src/prompts/funny_tutor_em.txt"))
    assert "Canonical 来源只读" in prompt
    assert "新生成的教学内容独立负责准确性" in prompt
    assert "JSON 字符串中的 LaTeX 必须正确转义" in prompt
    assert "独立求解后再验证" in prompt
    assert "一个合法 JSON 对象" in prompt
    assert "funny_explanation" in prompt
    assert "memory_aids" in prompt
    assert "common_misconceptions" in prompt
    assert "knowledge_main" in prompt
    assert "只生成 Funny Tutor 展示层字段" in prompt


def test_complete_json_uses_ollama_thinking_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[dict] = []

    responses = [
        '{"funny_explanation":"这题先看关系式。","memory_aids":["先看公式。"],"common_misconceptions":["别把电场强度和电荷量正相关。"]}',
        '{"ok":true}',
    ]

    def fake_completion(**kwargs):
        captured_calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(
                    content=responses[len(captured_calls) - 1]
                )
            )]
        )

    import src.llm_client as module
    monkeypatch.setattr(module.litellm, "completion", fake_completion)

    client = LLMClient(
        LLMConfig(
            model="ollama_chat/qwen3.5:9b-opencode",
            api_base="http://localhost:11434",
            think_generate=False,
            think_verify=True,
        ),
        "SYSTEM",
    )

    result_generate = client.complete_json(
        question_id="em-generate",
        user_prompt="Generate missing fields.",
        mode="generate",
    )
    result_verify = client.complete_json(
        question_id="em-verify",
        user_prompt="Verify independently.",
        mode="verify",
    )

    assert result_generate == {
        "funny_explanation": "这题先看关系式。",
        "memory_aids": ["先看公式。"],
        "common_misconceptions": ["别把电场强度和电荷量正相关。"],
    }
    assert result_verify == {"ok": True}
    assert len(captured_calls) == 2

    generate_call, verify_call = captured_calls
    assert generate_call["model"] == "ollama_chat/qwen3.5:9b-opencode"
    assert generate_call["api_base"] == "http://localhost:11434"
    assert generate_call["think"] is False
    assert generate_call["temperature"] == 0.0
    assert generate_call["response_format"]["type"] == "json_schema"
    assert (
        generate_call["response_format"]["json_schema"]["schema"]
        == FunnyTutorPayload.model_json_schema()
    )
    assert verify_call["think"] is True
    assert generate_call["messages"][0]["role"] == "system"
    assert "MODE: GENERATE" in generate_call["messages"][1]["content"]
    assert "MODE: VERIFY" in verify_call["messages"][1]["content"]
    assert "provided answer as a reasoning premise" in verify_call["messages"][1]["content"]


def test_non_ollama_model_does_not_receive_ollama_think_kwarg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        LLMConfig(model="gemini/gemini-2.5-pro"),
        "SYSTEM",
    )
    result = client.complete_json(
        question_id="cloud-001",
        user_prompt="Do the task.",
        mode="verify",
    )

    assert result == {"ok": True}
    assert captured["model"] == "gemini/gemini-2.5-pro"
    assert "think" not in captured


def test_complete_json_rejects_invalid_generate_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_completion(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(
                    content='{"knowledge_main":{"name":"不允许"}}'
                )
            )]
        )

    import src.llm_client as module
    monkeypatch.setattr(module.litellm, "completion", fake_completion)

    client = LLMClient(
        LLMConfig(model="ollama_chat/qwen3.5:9b-opencode"),
        "SYSTEM",
    )

    with pytest.raises(
        LLMResponseError,
        match="em-invalid.*invalid Generate payload",
    ):
        client.complete_json(
            question_id="em-invalid",
            user_prompt="Generate Funny Tutor fields.",
            mode="generate",
        )



def test_complete_json_rejects_control_character_corrupting_latex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_completion(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(
                    content = '{"funny_explanation":"m=' + chr(92) + 'rho V","memory_aids":["a"],"common_misconceptions":["b"]}'
                )
            )]
        )

    import src.llm_client as module
    monkeypatch.setattr(module.litellm, "completion", fake_completion)
    client = LLMClient(
        LLMConfig(model="ollama_chat/qwen3.5:9b-opencode"),
        "SYSTEM",
    )

    with pytest.raises(LLMResponseError, match="integrity check failed"):
        client.complete_json(
            question_id="em-control",
            user_prompt="Generate Funny Tutor fields.",
            mode="generate",
        )
