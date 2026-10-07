#!/usr/bin/env python3
"""Run the formal Funny Tutor Task 2 Verify A/B test.

This test uses the real application path:

    LLMClient -> LiteLLM -> Ollama -> qwen3.5:9b-opencode

It intentionally uses the values currently in config.toml:
    think_verify = true
    timeout = 1800

Usage:
    python test_logs/test_verify_think_on_ab.py         test_logs/test_verify_think_on_ab.log

Cases:
    A: provided answer is the correct answer B -> expect model_answer B + match
    B: provided answer is intentionally wrong D -> expect model_answer B + mismatch

The expected answer/verdict are external test oracles and are NOT included in
the model prompt.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.llm_client import LLMClient, load_llm_config, load_system_prompt  # noqa: E402
from test_logs.test_verify_think_off_ab import (  # noqa: E402
    EXPECTED_MODEL_ANSWER,
    TEST_CASES,
    build_user_prompt,
    load_question,
)

CONFIG_FILE = REPO_ROOT / "config.toml"
PROMPT_FILE = REPO_ROOT / "src" / "prompts" / "funny_tutor_em.txt"


def get_litellm_version() -> str:
    try:
        return importlib.metadata.version("litellm")
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def run_case(
    client: LLMClient,
    question: str,
    case: dict[str, Any],
    log,
) -> bool:
    case_id = case["id"].replace("task2-verify-think-off-", "task2-verify-think-on-")
    provided_answer = case["provided_answer"]
    expected_verdict = case["expected_verdict"]

    user_prompt = build_user_prompt(question, provided_answer)

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

    started = time.monotonic()
    try:
        result = client.complete_json(
            question_id=case_id,
            user_prompt=user_prompt,
            mode="verify",
        )
        elapsed = time.monotonic() - started
    except Exception as exc:
        elapsed = time.monotonic() - started
        log(f"EXCEPTION after {elapsed:.3f}s:")
        log(f"  type={type(exc).__name__}")
        log(f"  message={exc}")
        log("ASSESSMENT: FAIL (formal LLMClient/LiteLLM call did not return)")
        return False

    model_answer = result.get("model_answer")
    verdict = result.get("verdict")

    answer_ok = model_answer == EXPECTED_MODEL_ANSWER
    verdict_ok = verdict == expected_verdict
    passed = answer_ok and verdict_ok

    log(f"Elapsed: {elapsed:.3f}s")
    log("PARSED MODEL RESULT:")
    log(json.dumps(result, ensure_ascii=False, indent=2))
    log(
        f"Check model_answer == {EXPECTED_MODEL_ANSWER}: "
        f"{'PASS' if answer_ok else 'FAIL'}"
    )
    log(
        f"Check verdict == {expected_verdict!r}: "
        f"{'PASS' if verdict_ok else 'FAIL'}"
    )
    log(f"ASSESSMENT: {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run formal Funny Tutor think=True Verify A/B test."
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

        log("Funny Tutor — Task 2 formal Verify A/B test (think=True)")
        log(f"Started (UTC): {datetime.now(timezone.utc).isoformat()}")
        log(f"Repository root: {REPO_ROOT}")
        log(f"Config: {CONFIG_FILE}")
        log(f"System prompt: {PROMPT_FILE}")
        log(f"Output log: {log_path}")

        try:
            config = load_llm_config(CONFIG_FILE)
            system_prompt = load_system_prompt(PROMPT_FILE)
            question_record = load_question()
        except Exception as exc:
            log(f"SETUP FAILURE: {type(exc).__name__}: {exc}")
            return 1

        log("")
        log("RUNTIME CONFIGURATION:")
        log(f"  model={config.model}")
        log(f"  api_base={config.api_base}")
        log(f"  timeout={config.timeout}s")
        log(f"  think_generate={config.think_generate}")
        log(f"  think_verify={config.think_verify}")
        log(f"  litellm_version={get_litellm_version()}")
        log("  test_override=NONE (uses config.toml as-is)")

        log("")
        log("TARGET QUESTION:")
        log(
            f"  year={question_record.get('year')}, "
            f"category={question_record.get('category')}, "
            f"index={question_record.get('index')}"
        )
        log("  Complete question loaded from data/questions_em.json.")
        log(f"  Fixture answer (external oracle)={question_record.get('answer')}")

        client = LLMClient(config, system_prompt)

        results: list[bool] = []
        for case in TEST_CASES:
            results.append(
                run_case(
                    client,
                    question_record["question"],
                    case,
                    log,
                )
            )

        passed_count = sum(results)
        total = len(results)

        log("")
        log("=" * 88)
        log(f"FINAL RESULT: {passed_count}/{total} test cases passed")
        if passed_count == total:
            log(
                "Interpretation: formal Funny Tutor Verify path passed both "
                "correct-answer and intentionally-wrong-answer cases."
            )
        else:
            log(
                "Interpretation: formal Verify path did not fully pass. "
                "Inspect model answer/verdict and elapsed time before changing code."
            )
        log(f"Finished (UTC): {datetime.now(timezone.utc).isoformat()}")

    return 0 if passed_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
