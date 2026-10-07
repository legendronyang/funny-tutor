#!/usr/bin/env python3
"""Run the clean CPU-only Verify A/B experiment for Task 2.

Usage:
    python test_logs/test_verify_think_off_ab.py test_logs/test_verify_think_off_ab.log

The script:
1. Loads the complete 2010 全国卷Ⅱ rain-drop question from the project fixture.
2. Temporarily sets think_verify=False without changing config.toml.
3. Runs two Verify cases:
   - A: provided answer is the correct answer B.
   - B: provided answer is intentionally wrong (D).
4. Keeps the expected result OUT of the model prompt.
5. Writes the full experiment record, prompts, model results, and PASS/FAIL
   assessment to the log file supplied as the only argument.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.llm_client import LLMClient, load_llm_config, load_system_prompt  # noqa: E402


QUESTION_FILE = REPO_ROOT / "data" / "questions_em.json"
CONFIG_FILE = REPO_ROOT / "config.toml"
PROMPT_FILE = REPO_ROOT / "src" / "prompts" / "funny_tutor_em.txt"

QUESTION_YEAR = "2010"
QUESTION_CATEGORY = "（全国卷ⅱ）"
QUESTION_INDEX = 1

EXPECTED_MODEL_ANSWER = ["B"]
TEST_CASES = [
    {
        "id": "task2-verify-think-off-A",
        "provided_answer": ["B"],
        "expected_verdict": "match",
    },
    {
        "id": "task2-verify-think-off-B",
        "provided_answer": ["D"],
        "expected_verdict": "mismatch",
    },
]


def load_question() -> dict[str, Any]:
    with QUESTION_FILE.open("r", encoding="utf-8") as handle:
        questions = json.load(handle)

    matches = [
        question
        for question in questions
        if question.get("year") == QUESTION_YEAR
        and question.get("category") == QUESTION_CATEGORY
        and question.get("index") == QUESTION_INDEX
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one target question, found {len(matches)}: "
            f"{QUESTION_YEAR} {QUESTION_CATEGORY} index={QUESTION_INDEX}"
        )
    question = matches[0]
    if question.get("answer") != EXPECTED_MODEL_ANSWER:
        raise RuntimeError(
            "Test oracle changed unexpectedly: "
            f"fixture answer={question.get('answer')!r}, "
            f"expected={EXPECTED_MODEL_ANSWER!r}"
        )
    return question


def build_user_prompt(question: str, provided_answer: list[str]) -> str:
    return f"""请独立求解下面的物理题，然后再验证题库已有答案。

【题目】
{question}

【题库已有答案】
{json.dumps(provided_answer, ensure_ascii=False)}

【验证要求】
1. 必须先独立完成物理推导并得到你自己的答案。
2. 不得把“题库已有答案”作为推理前提。
3. 得到自己的结论以后，才能把它与题库已有答案比较。
4. model_answer 必须填写你独立求解得到的选项。
5. verdict 只能是 match、mismatch 或 uncertain。
6. explanation 说明你的独立计算/推理以及最后的比较结论。
7. 只输出一个合法 JSON 对象，不要输出 Markdown 代码块，不要输出 JSON 之外的文字。

输出结构只能遵循下面的字段结构；其中内容必须由你实际求解后填写：
{{
  "model_answer": ["..."],
  "verdict": "match | mismatch | uncertain",
  "explanation": "..."
}}
"""


def run_case(
    client: LLMClient,
    question: str,
    case: dict[str, Any],
    log,
) -> bool:
    case_id = case["id"]
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
        log(f"EXCEPTION after {elapsed:.2f}s: {type(exc).__name__}: {exc}")
        log("ASSESSMENT: FAIL (LLM call did not return a valid JSON result)")
        return False

    model_answer = result.get("model_answer")
    verdict = result.get("verdict")

    answer_ok = model_answer == EXPECTED_MODEL_ANSWER
    verdict_ok = verdict == expected_verdict
    passed = answer_ok and verdict_ok

    log(f"Elapsed: {elapsed:.2f}s")
    log("MODEL RESULT:")
    log(json.dumps(result, ensure_ascii=False, indent=2))
    log(f"Check model_answer == {EXPECTED_MODEL_ANSWER}: {'PASS' if answer_ok else 'FAIL'}")
    log(f"Check verdict == {expected_verdict!r}: {'PASS' if verdict_ok else 'FAIL'}")
    log(f"ASSESSMENT: {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the clean Task 2 think=False Verify A/B experiment."
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

    # Log both to stdout and to the requested file.
    with log_path.open("w", encoding="utf-8") as log_file:

        def log(message: str = "") -> None:
            print(message, flush=True)
            log_file.write(message + "\n")
            log_file.flush()

        log("Funny Tutor — Task 2 Verify A/B think=False experiment")
        log(f"Started (UTC): {datetime.now(timezone.utc).isoformat()}")
        log(f"Repository root: {REPO_ROOT}")
        log(f"Question fixture: {QUESTION_FILE}")
        log(f"Config: {CONFIG_FILE}")
        log(f"System prompt: {PROMPT_FILE}")
        log(f"Output log: {log_path}")

        try:
            question_record = load_question()
            config = load_llm_config(CONFIG_FILE)
            system_prompt = load_system_prompt(PROMPT_FILE)
        except Exception as exc:
            log(f"SETUP FAILURE: {type(exc).__name__}: {exc}")
            return 1

        # IMPORTANT: do not modify config.toml. This is a temporary experiment.
        test_config = replace(config, think_verify=False)
        client = LLMClient(test_config, system_prompt)

        log("")
        log("FORMAL CONFIGURATION:")
        log(f"  model={config.model}")
        log(f"  api_base={config.api_base}")
        log(f"  think_generate={config.think_generate}")
        log(f"  think_verify={config.think_verify}")
        log("TEMPORARY TEST OVERRIDE:")
        log(f"  think_verify={test_config.think_verify}")
        log("")
        log("TARGET QUESTION:")
        log(
            f"  year={question_record.get('year')}, "
            f"category={question_record.get('category')}, "
            f"index={question_record.get('index')}"
        )
        log("  Complete question loaded from data/questions_em.json.")
        log(f"  Fixture answer (external oracle)={question_record.get('answer')}")

        results = []
        for case in TEST_CASES:
            results.append(run_case(client, question_record["question"], case, log))

        passed = sum(results)
        total = len(results)
        log("")
        log("=" * 88)
        log(f"FINAL RESULT: {passed}/{total} test cases passed")
        log("Interpretation:")
        if passed == total:
            log(
                "  Both A and B passed. The CPU think=False single-call Verify "
                "contract demonstrated the expected answer/verdict behavior "
                "for this clean test."
            )
        else:
            log(
                "  The clean A/B Verify experiment did NOT fully pass. "
                "Do not promote think=False Verify to the formal policy yet."
            )
        log(f"Finished (UTC): {datetime.now(timezone.utc).isoformat()}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
