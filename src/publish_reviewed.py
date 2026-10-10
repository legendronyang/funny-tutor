"""Promote a staged Markdown card only when its decision evidence says ACCEPT."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def publish_reviewed_card(
    *,
    candidate_card: Path,
    decision_file: Path,
    destination: Path,
    question_id: str,
) -> Path:
    """Copy a candidate card only after validating matching ACCEPT evidence."""
    if not candidate_card.is_file():
        raise FileNotFoundError(f"Candidate card does not exist: {candidate_card}")
    if candidate_card.stem != question_id:
        raise ValueError("Candidate card filename stem does not match question_id")
    if destination.stem != question_id:
        raise ValueError("Destination filename stem does not match question_id")
    evidence: dict[str, Any] = json.loads(decision_file.read_text(encoding="utf-8"))
    decision = evidence.get("decision", {})
    if decision.get("question_id") != question_id:
        raise ValueError("Decision evidence question_id does not match requested question")
    if decision.get("decision") != "ACCEPT":
        raise ValueError(
            f"Publication blocked: decision is {decision.get('decision')!r}, not 'ACCEPT'"
        )

    reports = evidence.get("reports")
    if not isinstance(reports, list):
        raise ValueError("Decision evidence is missing the structured review reports")
    matching_reports = [
        report for report in reports
        if isinstance(report, dict) and report.get("question_id") == question_id
    ]
    if len(matching_reports) != len(reports):
        raise ValueError("Publication blocked: evidence contains reports for another question")
    reviewers = {
        report.get("reviewer_model", "").strip().casefold()
        for report in matching_reports
        if isinstance(report.get("reviewer_model"), str)
    }
    if len(reviewers) < 2:
        raise ValueError("Publication blocked: evidence must contain two distinct reviewers")
    required_checks = (
        "answer_correctness",
        "physics_reasoning",
        "formula_units",
        "numerical_consistency",
        "student_clarity",
        "latex_integrity",
    )
    for report in matching_reports:
        if report.get("canonical_answer_match") != "MATCH":
            raise ValueError("Publication blocked: independent answer did not match canonical answer")
        if report.get("issues"):
            raise ValueError("Publication blocked: reviewer reported unresolved issues")
        for check_name in required_checks:
            check = report.get(check_name)
            if not isinstance(check, dict) or check.get("status") != "PASS":
                raise ValueError(
                    f"Publication blocked: {report.get('reviewer_model')} "
                    f"did not pass {check_name}"
                )
            if check.get("issues"):
                raise ValueError(
                    f"Publication blocked: {report.get('reviewer_model')} "
                    f"has unresolved issues in {check_name}"
                )

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidate_card, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-card", type=Path, required=True)
    parser.add_argument("--decision-file", type=Path, required=True)
    parser.add_argument("--question-id", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    result = publish_reviewed_card(
        candidate_card=args.candidate_card,
        decision_file=args.decision_file,
        destination=args.destination,
        question_id=args.question_id,
    )
    print(f"Published reviewed candidate: {result}")


if __name__ == "__main__":
    main()
