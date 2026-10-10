"""Tests for deterministic text integrity and conservative publication decisions."""

from __future__ import annotations

import pytest

from src.quality_gate import (
    build_review_report,
    decide_publication,
    find_forbidden_control_characters,
    validate_generated_payload_text,
)


def passing_review_payload() -> dict:
    passed = {"status": "PASS", "evidence": ["推导逐步成立。"], "issues": []}
    return {
        "answer_correctness": passed,
        "physics_reasoning": passed,
        "formula_units": passed,
        "numerical_consistency": passed,
        "student_clarity": passed,
        "latex_integrity": passed,
        "issues": [],
    }


def report(model: str, answer: list[str] | None = None, payload: dict | None = None):
    return build_review_report(
        question_id="q1",
        reviewer_model=model,
        independent_answer=answer or ["B"],
        canonical_answer=["B"],
        review_payload=payload or passing_review_payload(),
    )


def test_latex_backslashes_survive_as_plain_text() -> None:
    validate_generated_payload_text({
        "funny_explanation": r"质量为 $m=\rho V$，并使用 $\frac{4}{3}$。",
        "memory_aids": [r"注意 $\text{单位}$。"],
        "common_misconceptions": ["不要混淆质量与重力。"],
    })


@pytest.mark.parametrize("bad", ["回车\r断裂", "制表\t断裂", "换页\f断裂", "空字符\x00"])
def test_control_characters_are_detected(bad: str) -> None:
    assert find_forbidden_control_characters(bad)
    with pytest.raises(ValueError, match="control characters"):
        validate_generated_payload_text({
            "funny_explanation": bad,
            "memory_aids": ["记忆公式。"],
            "common_misconceptions": ["单位换算。"],
        })


def test_two_distinct_passing_reviewers_can_accept() -> None:
    decision = decide_publication(
        question_id="q1",
        canonical_answer=["B"],
        reports=[report("provider/model-a"), report("provider/model-b")],
    )
    assert decision.decision == "ACCEPT"
    assert decision.distinct_reviewers == 2


def test_one_reviewer_is_not_enough_even_if_it_passes() -> None:
    decision = decide_publication(
        question_id="q1",
        canonical_answer=["B"],
        reports=[report("provider/model-a")],
    )
    assert decision.decision == "REVIEW"


def test_same_model_twice_does_not_count_as_independent_reviewers() -> None:
    decision = decide_publication(
        question_id="q1",
        canonical_answer=["B"],
        reports=[report("provider/model-a"), report("provider/model-a")],
    )
    assert decision.decision == "REVIEW"
    assert decision.distinct_reviewers == 1


def test_reviewers_disagreeing_on_answer_go_to_review() -> None:
    decision = decide_publication(
        question_id="q1",
        canonical_answer=["B"],
        reports=[report("provider/model-a", ["B"]), report("provider/model-b", ["C"])],
    )
    assert decision.decision == "REVIEW"


def test_explicit_critical_failure_rejects_candidate() -> None:
    payload = passing_review_payload()
    payload["formula_units"] = {
        "status": "FAIL",
        "evidence": ["分母量纲不一致。"],
        "issues": ["公式量纲错误。"],
    }
    decision = decide_publication(
        question_id="q1",
        canonical_answer=["B"],
        reports=[
            report("provider/model-a", payload=payload),
            report("provider/model-b"),
        ],
    )
    assert decision.decision == "REJECT"


def test_uncertainty_never_auto_accepts() -> None:
    payload = passing_review_payload()
    payload["student_clarity"] = {
        "status": "UNCERTAIN",
        "evidence": ["该表述存在两种理解。"],
        "issues": ["需要人工确认。"],
    }
    decision = decide_publication(
        question_id="q1",
        canonical_answer=["B"],
        reports=[
            report("provider/model-a", payload=payload),
            report("provider/model-b"),
        ],
    )
    assert decision.decision == "REVIEW"


def test_answer_comparison_is_computed_by_application() -> None:
    value = report("provider/model-a", ["C"])
    assert value.canonical_answer_match == "MISMATCH"
