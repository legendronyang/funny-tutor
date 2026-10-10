"""Deterministic integrity checks and conservative multi-review publication policy."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

try:
    from .schema import (
        PublicationDecision,
        ReviewReport,
    )
except ImportError:  # pragma: no cover - supports direct script execution
    from schema import PublicationDecision, ReviewReport


REVIEW_DIMENSIONS = (
    "answer_correctness",
    "physics_reasoning",
    "formula_units",
    "numerical_consistency",
    "student_clarity",
    "latex_integrity",
)

# LF is allowed for paragraph breaks. CR, TAB, FF, NUL and other ASCII controls
# are not valid in generated prose because JSON escapes such as \\r, \\t and
# \\f can otherwise split or corrupt LaTeX in the final Markdown.
def find_forbidden_control_characters(text: str) -> list[tuple[int, str]]:
    """Return forbidden control characters as (index, Unicode code point)."""
    findings: list[tuple[int, str]] = []
    for index, char in enumerate(text):
        codepoint = ord(char)
        if (codepoint < 32 and char != "\n") or codepoint == 127:
            findings.append((index, f"U+{codepoint:04X}"))
    return findings


def validate_generated_payload_text(payload: Mapping[str, Any]) -> None:
    """Raise ValueError if generated text contains control characters."""
    text_fields: list[tuple[str, str]] = []
    explanation = payload.get("funny_explanation")
    if isinstance(explanation, str):
        text_fields.append(("funny_explanation", explanation))

    for field in ("memory_aids", "common_misconceptions"):
        values = payload.get(field)
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
            text_fields.extend(
                (f"{field}[{index}]", value)
                for index, value in enumerate(values)
                if isinstance(value, str)
            )

    errors: list[str] = []
    for field, value in text_fields:
        for index, codepoint in find_forbidden_control_characters(value):
            errors.append(f"{field} contains {codepoint} at character index {index}")

    if errors:
        raise ValueError(
            "Generated payload contains forbidden control characters: "
            + "; ".join(errors)
        )


def _normalize_answer(answer: Sequence[str]) -> tuple[str, ...]:
    """Normalize common multiple-choice forms such as ['AC'] and ['A', 'C']."""
    values = [str(item).strip().upper() for item in answer if str(item).strip()]
    if values and all(re.fullmatch(r"[A-D]+", item) for item in values):
        return tuple(sorted({letter for item in values for letter in item}))
    return tuple(sorted(values))


def decide_publication(
    *,
    question_id: str,
    canonical_answer: Sequence[str],
    reports: Sequence[ReviewReport],
    minimum_reviewers: int = 2,
) -> PublicationDecision:
    """Aggregate independent reviews without majority-voting away a real concern.

    Any explicit critical FAIL blocks publication. Reviewer disagreement, an
    answer disagreement with the canonical source, missing reviewers or any
    UNCERTAIN check sends the candidate to REVIEW rather than silently passing.
    """
    if minimum_reviewers < 2:
        raise ValueError("minimum_reviewers must be at least 2")

    matching_reports = [report for report in reports if report.question_id == question_id]
    foreign_reports = [report for report in reports if report.question_id != question_id]
    reasons: list[str] = []
    if foreign_reports:
        reasons.append("One or more review reports belong to another question.")
    unique_models = {report.reviewer_model.strip().casefold() for report in matching_reports}
    unique_models.discard("")
    distinct_reviewers = len(unique_models)

    if distinct_reviewers < minimum_reviewers:
        reasons.append(
            f"Need at least {minimum_reviewers} distinct reviewers; "
            f"received {distinct_reviewers}."
        )

    if not matching_reports:
        reasons.append("No valid review report is available for this question.")
        return PublicationDecision(
            question_id=question_id,
            decision="REVIEW",
            distinct_reviewers=distinct_reviewers,
            reasons=reasons,
        )

    failed_checks: list[str] = []
    uncertain_checks: list[str] = []
    for report in matching_reports:
        if report.issues:
            uncertain_checks.append(
                f"{report.reviewer_model}: reviewer reported unresolved issues: "
                + "; ".join(report.issues)
            )
        for dimension in REVIEW_DIMENSIONS:
            check = getattr(report, dimension)
            if check.status == "FAIL":
                failed_checks.append(
                    f"{report.reviewer_model}: {dimension} failed "
                    f"({'; '.join(check.issues) or '; '.join(check.evidence)})."
                )
            elif check.status == "UNCERTAIN":
                uncertain_checks.append(f"{report.reviewer_model}: {dimension} is uncertain.")
            elif check.issues:
                uncertain_checks.append(
                    f"{report.reviewer_model}: {dimension} has unresolved issues: "
                    + "; ".join(check.issues)
                )

    normalized_answers = {
        _normalize_answer(report.independent_answer)
        for report in matching_reports
    }
    if len(normalized_answers) > 1:
        reasons.append("Independent reviewers disagree on the solved answer.")

    canonical_normalized = _normalize_answer(canonical_answer)
    if not canonical_normalized:
        reasons.append("Canonical answer is empty and requires review.")
    elif any(answer != canonical_normalized for answer in normalized_answers):
        reasons.append(
            "At least one independent solution differs from the canonical answer; "
            "inspect the source answer and reasoning before release."
        )

    if failed_checks:
        reasons.extend(failed_checks)
        decision = "REJECT"
    elif (
        foreign_reports
        or distinct_reviewers < minimum_reviewers
        or len(normalized_answers) > 1
        or not canonical_normalized
        or any(answer != canonical_normalized for answer in normalized_answers)
        or uncertain_checks
        or any(report.canonical_answer_match == "UNCERTAIN" for report in matching_reports)
        or any(report.canonical_answer_match == "MISMATCH" for report in matching_reports)
    ):
        reasons.extend(uncertain_checks)
        decision = "REVIEW"
    else:
        reasons.append(
            "All required checks passed, distinct reviewers agree, and the independently "
            "derived answer matches the canonical answer. This is evidence-based acceptance, "
            "not a proof of absolute correctness."
        )
        decision = "ACCEPT"

    return PublicationDecision(
        question_id=question_id,
        decision=decision,
        distinct_reviewers=distinct_reviewers,
        reasons=reasons or ["Review decision requires inspection."],
        compared_answer=list(next(iter(normalized_answers))) if len(normalized_answers) == 1 else [],
    )


def build_review_report(
    *,
    question_id: str,
    reviewer_model: str,
    independent_answer: Sequence[str],
    canonical_answer: Sequence[str],
    review_payload: Mapping[str, Any],
) -> ReviewReport:
    """Validate a model review and enrich it with application-computed answer match."""
    try:
        from .schema import ReviewReportPayload
    except ImportError:  # pragma: no cover
        from schema import ReviewReportPayload

    try:
        payload = ReviewReportPayload.model_validate(review_payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid review payload for {question_id}: {exc}") from exc

    independent = _normalize_answer(independent_answer)
    canonical = _normalize_answer(canonical_answer)
    if not independent or not canonical:
        match = "UNCERTAIN"
    elif independent == canonical:
        match = "MATCH"
    else:
        match = "MISMATCH"

    return ReviewReport(
        question_id=question_id,
        reviewer_model=reviewer_model,
        independent_answer=list(independent_answer),
        canonical_answer_match=match,
        answer_correctness=payload.answer_correctness,
        physics_reasoning=payload.physics_reasoning,
        formula_units=payload.formula_units,
        numerical_consistency=payload.numerical_consistency,
        student_clarity=payload.student_clarity,
        latex_integrity=payload.latex_integrity,
        issues=payload.issues,
    )

