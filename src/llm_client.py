"""LiteLLM-backed provider-independent client for Funny Tutor."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import litellm
from dotenv import load_dotenv
from pydantic import ValidationError

try:
    from .quality_gate import validate_generated_payload_text
    from .schema import FunnyTutorPayload
except ImportError:  # pragma: no cover - supports direct script execution
    from quality_gate import validate_generated_payload_text
    from schema import FunnyTutorPayload

LOGGER = logging.getLogger(__name__)

# These TeX commands begin with letters that are also valid JSON escape
# introducers (\\b, \\f, \\n, \\r, \\t). If a model emits one backslash in a
# JSON string, json.loads may turn the command prefix into a control char.
# Repair only recognizable TeX command names; unknown controls stay rejected.
_LATEX_COMMANDS = tuple(sorted({
    "begin", "big", "Big", "bigg", "Bigg", "bf", "boldsymbol", "boxed",
    "brack", "frac", "fbox", "neq", "nabla", "nexists", "not", "rho",
    "right", "rightarrow", "rangle", "rm", "text", "textbf", "textit",
    "texttt", "times", "theta", "tilde", "tau", "tan", "triangle",
    "top", "to", "therefore", "tfrac", "thinspace", "thickspace",
}, key=len, reverse=True))


def _is_latex_command_at(text: str, index: int) -> bool:
    for command in _LATEX_COMMANDS:
        if not text.startswith(command, index):
            continue
        end = index + len(command)
        if end == len(text) or not text[end].isalnum():
            return True
    return False


def _repair_unescaped_latex_commands(raw_json: str) -> tuple[str, int]:
    """Double single backslashes for known TeX commands inside JSON strings.

    Correct JSON escapes are left untouched. This narrow repair is not general
    JSON sanitization; all remaining decoded controls are rejected downstream.
    """
    output: list[str] = []
    in_string = False
    repairs = 0
    index = 0

    while index < len(raw_json):
        char = raw_json[index]
        if not in_string:
            output.append(char)
            if char == '"':
                in_string = True
            index += 1
            continue

        if char == '"':
            output.append(char)
            in_string = False
            index += 1
            continue

        if char == "\\":
            if index + 1 >= len(raw_json):
                output.append(char)
                index += 1
                continue

            next_char = raw_json[index + 1]
            if next_char == "\\":
                # Already escaped in valid JSON.
                output.extend((char, next_char))
                index += 2
                continue

            if _is_latex_command_at(raw_json, index + 1):
                output.extend(("\\", "\\"))
                repairs += 1
                index += 1
                continue

            # Consume ordinary JSON escape pairs together so escaped quotes
            # do not accidentally terminate a JSON string.
            output.extend((char, next_char))
            index += 2
            continue

        output.append(char)
        index += 1

    return "".join(output), repairs


GenerationMode = Literal["generate", "verify"]


class LLMResponseError(ValueError):
    """Raised when an LLM response cannot be parsed as the expected JSON."""

    def __init__(self, question_id: str, reason: str) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id}: {reason}")


def decide_field_mode(value: Any) -> GenerationMode:
    """Return generate for empty values, otherwise verify."""
    if value is None:
        return "generate"
    if isinstance(value, str) and not value.strip():
        return "generate"
    if isinstance(value, (list, tuple, dict)) and not value:
        return "generate"
    return "verify"


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    fenced = re.fullmatch(r"\`\`\`(?:json)?\s*(.*?)\s*\`\`\`", text, flags=re.DOTALL)
    return fenced.group(1).strip() if fenced else text


def parse_json_response(raw_text: str, question_id: str) -> dict[str, Any]:
    """Extract and parse the first JSON object from an LLM response."""
    if not raw_text or not raw_text.strip():
        raise LLMResponseError(question_id, "LLM returned empty content")

    candidate = _strip_code_fence(raw_text)
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", candidate):
        candidate_json = candidate[match.start() :]
        repaired_json, repair_count = _repair_unescaped_latex_commands(candidate_json)
        try:
            value, _ = decoder.raw_decode(repaired_json)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            if repair_count:
                LOGGER.warning(
                    "Repaired %d unescaped LaTeX command backslash(es) in response for %s; "
                    "the decoded text will still be checked for forbidden controls",
                    repair_count,
                    question_id,
                )
            return value

    raise LLMResponseError(
        question_id,
        "unable to extract a valid JSON object from LLM response",
    )


def validate_funny_payload(
    payload: dict[str, Any],
    question_id: str,
) -> FunnyTutorPayload:
    """Validate the strict Generate payload before it reaches the renderer."""
    try:
        validated = FunnyTutorPayload.model_validate(payload)
    except ValidationError as exc:
        raise LLMResponseError(
            question_id,
            f"invalid Generate payload: {exc}",
        ) from exc

    try:
        validate_generated_payload_text(payload)
    except ValueError as exc:
        raise LLMResponseError(
            question_id,
            f"generated text integrity check failed: {exc}",
        ) from exc

    return validated


@dataclass(frozen=True)
class LLMConfig:
    model: str
    api_base: str | None = None
    api_key_env: str | None = None
    timeout: int = 180
    temperature: float = 0.0
    think_generate: bool = False
    think_verify: bool = True


def load_llm_config(config_path: Path) -> LLMConfig:
    """Load the [llm] section from config.toml."""
    load_dotenv()
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    section = raw.get("llm", {})
    model = section.get("model")
    if not isinstance(model, str) or not model.strip() or model == "SET_ME":
        raise ValueError("config.toml [llm].model must be a concrete LiteLLM model")

    api_base = section.get("api_base")
    api_key_env = section.get("api_key_env")
    return LLMConfig(
        model=model,
        api_base=api_base if isinstance(api_base, str) and api_base else None,
        api_key_env=api_key_env if isinstance(api_key_env, str) and api_key_env else None,
        timeout=int(section.get("timeout", 180)),
        temperature=float(section.get("temperature", 0.0)),
        think_generate=bool(section.get("think_generate", False)),
        think_verify=bool(section.get("think_verify", True)),
    )


def load_system_prompt(prompt_path: Path) -> str:
    """Load and validate the Funny Tutor system prompt."""
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError(f"Prompt file is empty: {prompt_path}")
    return prompt


class LLMClient:
    """Single integration point between Funny Tutor and LiteLLM."""

    def __init__(self, config: LLMConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt

    def _thinking_for_mode(self, mode: GenerationMode) -> bool:
        return self.config.think_generate if mode == "generate" else self.config.think_verify

    def complete_json(
        self,
        *,
        question_id: str,
        user_prompt: str,
        mode: GenerationMode,
    ) -> dict[str, Any]:
        """Call the configured model and return one parsed JSON object."""
        mode_instruction = (
            "MODE: GENERATE\nGenerate missing target fields."
            if mode == "generate"
            else (
                "MODE: VERIFY\n"
                "Solve independently first; compare only after reaching your own conclusion. "
                "Do not use the provided answer as a reasoning premise."
            )
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"{mode_instruction}\n\n{user_prompt}"},
        ]

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "timeout": self.config.timeout,
        }
        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base
        if self.config.api_key_env:
            api_key = os.getenv(self.config.api_key_env)
            if not api_key:
                raise RuntimeError(
                    f"Environment variable {self.config.api_key_env} is not set"
                )
            kwargs["api_key"] = api_key

        if mode == "generate":
            model_lower = self.config.model.lower()
            # Gemini 3 models no longer accept legacy sampling parameters such
            # as temperature. Keep this provider-family compatibility rule in
            # the client rather than leaking it into generation/pipeline code.
            is_gemini_3 = model_lower.startswith("gemini/") and (
                model_lower.split("/", 1)[1].startswith("gemini-3")
            )
            if not is_gemini_3:
                kwargs["temperature"] = self.config.temperature

        # Ollama's chat endpoint exposes Qwen thinking as the 'think' parameter.
        # Keep this provider-specific mapping inside the client so upper layers
        # remain provider-agnostic. Cloud providers do not receive this kwarg.
        if self.config.model.startswith("ollama_chat/"):
            kwargs["think"] = self._thinking_for_mode(mode)
            if mode == "generate":
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "schema": FunnyTutorPayload.model_json_schema(),
                    },
                }

        try:
            response = litellm.completion(**kwargs)
            raw = response.choices[0].message.content
        except Exception as exc:
            raise RuntimeError(
                f"Question {question_id}: LiteLLM call failed: {exc}"
            ) from exc

        if not isinstance(raw, str):
            raise LLMResponseError(question_id, "LLM response content is not text")
        payload = parse_json_response(raw, question_id)
        if mode == "generate":
            return validate_funny_payload(payload, question_id).model_dump(mode="json")
        return payload
