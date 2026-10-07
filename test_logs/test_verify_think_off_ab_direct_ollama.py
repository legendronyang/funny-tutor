#!/usr/bin/env python3
"""Diagnose Task 2 Verify think=False directly against Ollama.

Usage:
    python test_logs/test_verify_think_off_ab_direct_ollama.py \
        test_logs/test_verify_think_off_ab_direct_ollama.log

This experiment keeps the same question and user prompts as
test_verify_think_off_ab.py, but bypasses LiteLLM and LLMClient entirely.

The script sends:
    POST http://localhost:11434/api/chat
with:
    "think": false
    "stream": false

It records Ollama's native timing fields so we can distinguish:
1. Ollama/Qwen generation slowness, from
2. LiteLLM/LLMClient overhead or timeout behavior.

The expected answer/verdict is never included in the model prompt.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from test_logs.test_verify_think_off_ab import (  # noqa: E402
    EXPECTED_MODEL_ANSWER,
    TEST_CASES,
    build_user_prompt,
    load_question,
)
from src.llm_client import load_llm_config, load_system_prompt  # noqa: E402


CONFIG_FILE = REPO_ROOT / "config.toml"
PROMPT_FILE = REPO_ROOT / "src" / "prompts" / "funny_tutor_em.txt"

OLLAMA_API = "http://localhost:11434/api/chat"
OLLAMA_MODEL_PREFIX = "ollama_chat/"
HTTP_TIMEOUT_SECONDS = 240


def log_subprocess_output(log, command: list[str]) -> None:
    log("")
    log(f"$ {' '.join(command)}")
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.stdout.strip():
            log(completed.stdout.rstrip())
        if completed.stderr.strip():
            log("STDERR:")
            log(completed.stderr.rstrip())
        log(f"returncode={completed.returncode}")
    except Exception as exc:
        log(f"COMMAND ERROR: {type(exc).__name__}: {exc}")


def call_ollama(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> tuple[dict[str, Any], float]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "think": False,
        "stream": False,
    }

    request = Request(
        OLLAMA_API,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.monotonic()
    with urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8")
    elapsed = time.monotonic() - started

    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Ollama returned non-JSON response: {body[:1000]!r}"
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError(f"Ollama response is not a JSON object: {result!r}")

    return result, elapsed


def assess_result(
    result: dict[str, Any],
    expected_verdict: str,
) -> tuple[bool, dict[str, Any]]:
    message = result.get("message")
    if not isinstance(message, dict):
        return False, {
            "reason": "missing message object",
            "model_answer_ok": False,
            "verdict_ok": False,
        }

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return False, {
            "reason": "missing/empty message.content",
            "model_answer_ok": False,
            "verdict_ok": False,
        }

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return False, {
            "reason": "message.content is not valid JSON",
            "model_answer_ok": False,
            "verdict_ok": False,
            "raw_content": content,
        }

    if not isinstance(parsed, dict):
        return False, {
            "reason": "message.content JSON is not an object",
            "model_answer_ok": False,
            "verdict_ok": False,
            "parsed": parsed,
        }

    model_answer = parsed.get("model_answer")
    verdict = parsed.get("verdict")
    answer_ok = model_answer == EXPECTED_MODEL_ANSWER
    verdict_ok = verdict == expected_verdict
    passed = answer_ok and verdict_ok

    return passed, {
        "parsed_result": parsed,
        "model_answer_ok": answer_ok,
        "verdict_ok": verdict_ok,
        "expected_model_answer": EXPECTED_MODEL_ANSWER,
        "expected_verdict": expected_verdict,
        "reason": "PASS" if passed else "model result does not match external oracle",
    }


def log_timing(log, result: dict[str, Any], wall_elapsed: float) -> None:
    log("OLLAMA NATIVE TIMING:")
    timing_fields = [
        "total_duration",
        "load_duration",
        "prompt_eval_count",
        "prompt_eval_duration",
        "eval_count",
        "eval_duration",
    ]
    for field in timing_fields:
        value = result.get(field)
        if field.endswith("_duration") and isinstance(value, int):
            log(f"  {field}={value} ns ({value / 1_000_000_000:.3f}s)")
        else:
            log(f"  {field}={value!r}")

    log(f"  measured_wall_elapsed={wall_elapsed:.3f}s")

    total_duration = result.get("total_duration")
    eval_duration = result.get("eval_duration")
    eval_count = result.get("eval_count")

    if isinstance(eval_count, int) and isinstance(eval_duration, int) and eval_duration:
        log(f"  eval_tokens_per_second={eval_count / (eval_duration / 1_000_000_000):.3f}")

    if isinstance(total_duration, int):
        log(f"  native_total_seconds={total_duration / 1_000_000_000:.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run direct Ollama think=False Verify A/B diagnostics."
    )
    parser.add_argument(
        "logfile",
        help="Path of the log file to create/overwrite with the run result.",
    )
    args = parser.parse_args()

    log_path = Path(args.logfile).expanduser()
    if not log_path.is_absolute():
        log_path = Path.cwd() / log_path
    log_path = log_path.resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as log_file:

        def log(message: str = "") -> None:
            print(message, flush=True)
            log_file.write(message + "\n")
            log_file.flush()

        log("Funny Tutor — Task 2 direct Ollama Verify A/B think=False diagnostic")
        log(f"Started (UTC): {datetime.now(timezone.utc).isoformat()}")
        log(f"Repository root: {REPO_ROOT}")
        log(f"Config: {CONFIG_FILE}")
        log(f"System prompt: {PROMPT_FILE}")
        log(f"Ollama API: {OLLAMA_API}")
        log(f"HTTP timeout: {HTTP_TIMEOUT_SECONDS}s")
        log(f"Output log: {log_path}")

        try:
            config = load_llm_config(CONFIG_FILE)
            system_prompt = load_system_prompt(PROMPT_FILE)
            question_record = load_question()
        except Exception as exc:
            log(f"SETUP FAILURE: {type(exc).__name__}: {exc}")
            return 1

        model = config.model
        if model.startswith(OLLAMA_MODEL_PREFIX):
            model = model[len(OLLAMA_MODEL_PREFIX) :]

        log("")
        log("CONFIGURATION:")
        log(f"  configured LiteLLM model={config.model}")
        log(f"  direct Ollama model={model}")
        log(f"  configured api_base={config.api_base}")
        log(f"  formal think_generate={config.think_generate}")
        log(f"  formal think_verify={config.think_verify}")
        log("  direct test think=False")
        log(f"  question year={question_record.get('year')}")
        log(f"  question category={question_record.get('category')}")
        log(f"  question index={question_record.get('index')}")
        log(f"  fixture answer (external oracle)={question_record.get('answer')}")

        log_subprocess_output(log, ["ollama", "--version"])
        log_subprocess_output(log, ["ollama", "ps"])

        results: list[bool] = []

        for case in TEST_CASES:
            case_id = case["id"] + "-direct-ollama"
            provided_answer = case["provided_answer"]
            expected_verdict = case["expected_verdict"]
            user_prompt = build_user_prompt(
                question_record["question"],
                provided_answer,
            )

            log("")
            log("=" * 88)
            log(f"TEST CASE: {case_id}")
            log(f"Provided answer: {provided_answer}")
            log(f"External expected model_answer: {EXPECTED_MODEL_ANSWER}")
            log(f"External expected verdict: {expected_verdict}")
            log("-" * 88)
            log("USER PROMPT (expected result is intentionally NOT included):")
            log(user_prompt)
            log("-" * 88)

            try:
                result, wall_elapsed = call_ollama(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
            except (HTTPError, URLError, TimeoutError) as exc:
                log(
                    f"EXCEPTION: {type(exc).__name__}: {exc}"
                )
                log("ASSESSMENT: FAIL (direct Ollama HTTP call failed/timed out)")
                results.append(False)
                continue
            except Exception as exc:
                log(f"EXCEPTION: {type(exc).__name__}: {exc}")
                log("ASSESSMENT: FAIL (direct Ollama call failed)")
                results.append(False)
                continue

            log(f"WALL-CLOCK ELAPSED: {wall_elapsed:.3f}s")
            log_timing(log, result, wall_elapsed)

            message = result.get("message")
            if isinstance(message, dict):
                log("RAW MODEL CONTENT:")
                log(str(message.get("content", "")))

            log("")
            log("FULL OLLAMA RESPONSE:")
            log(json.dumps(result, ensure_ascii=False, indent=2))

            passed, assessment = assess_result(result, expected_verdict)
            log("")
            log("EXTERNAL ASSESSMENT:")
            log(json.dumps(assessment, ensure_ascii=False, indent=2))
            log(f"ASSESSMENT: {'PASS' if passed else 'FAIL'}")
            results.append(passed)

        log("")
        log("=" * 88)
        passed_count = sum(results)
        total = len(results)
        log(f"FINAL RESULT: {passed_count}/{total} test cases passed")
        log("Diagnostic interpretation:")
        if passed_count == total:
            log(
                "  Both direct Ollama tests passed. Compare native timing with "
                "the LiteLLM A/B log to determine remaining overhead."
            )
        else:
            log(
                "  Direct Ollama did not fully pass. If a direct call also "
                "times out, the bottleneck is below LiteLLM/LLMClient."
            )
        log(f"Finished (UTC): {datetime.now(timezone.utc).isoformat()}")

    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
