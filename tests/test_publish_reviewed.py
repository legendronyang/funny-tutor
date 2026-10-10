"""Tests for the explicit reviewed-card promotion boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.publish_reviewed import publish_reviewed_card


def test_only_matching_accept_decision_can_publish(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.md"
    candidate.write_text("# Candidate", encoding="utf-8")
    evidence = tmp_path / "decision.json"
    passed = {
        "status": "PASS",
        "evidence": ["具体推导证据"],
        "issues": [],
    }
    report = {
        "question_id": "q1",
        "reviewer_model": "provider/model-a",
        "canonical_answer_match": "MATCH",
        **{
            key: passed for key in (
                "answer_correctness", "physics_reasoning", "formula_units",
                "numerical_consistency", "student_clarity", "latex_integrity"
            )
        },
    }
    report_b = {**report, "reviewer_model": "provider/model-b"}
    evidence.write_text(json.dumps({
        "decision": {"question_id": "q1", "decision": "ACCEPT"},
        "reports": [report, report_b],
    }), encoding="utf-8")
    destination = tmp_path / "formal" / "q1.md"

    result = publish_reviewed_card(
        candidate_card=candidate,
        decision_file=evidence,
        destination=destination,
        question_id="q1",
    )

    assert result == destination
    assert destination.read_text(encoding="utf-8") == "# Candidate"


@pytest.mark.parametrize("decision", ["REVIEW", "REJECT", None])
def test_review_or_reject_decision_cannot_publish(tmp_path: Path, decision: str | None) -> None:
    candidate = tmp_path / "candidate.md"
    candidate.write_text("# Candidate", encoding="utf-8")
    evidence = tmp_path / "decision.json"
    evidence.write_text(json.dumps({
        "decision": {"question_id": "q1", "decision": decision}
    }), encoding="utf-8")
    destination = tmp_path / "formal" / "q1.md"

    with pytest.raises(ValueError, match="Publication blocked"):
        publish_reviewed_card(
            candidate_card=candidate,
            decision_file=evidence,
            destination=destination,
            question_id="q1",
        )

    assert not destination.exists()


def test_decision_for_another_question_cannot_publish(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.md"
    candidate.write_text("# Candidate", encoding="utf-8")
    evidence = tmp_path / "decision.json"
    evidence.write_text(json.dumps({
        "decision": {"question_id": "q2", "decision": "ACCEPT"}
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match"):
        publish_reviewed_card(
            candidate_card=candidate,
            decision_file=evidence,
            destination=tmp_path / "formal" / "q1.md",
            question_id="q1",
        )
