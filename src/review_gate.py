"""Validate reviewer JSON files and calculate a conservative publication decision.

Input JSON format:
{
  "question_id": "q1",
  "canonical_answer": ["B"],
  "reviews": [
    {
      "reviewer_model": "provider/model-name",
      "independent_answer": ["B"],
      "review": { "...": "ReviewReportPayload fields" }
    }
  ]
}

This CLI aggregates supplied evidence. It does not call models or prove correctness.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

try:
    from .quality_gate import build_review_report, decide_publication
except ImportError:  # pragma: no cover
    from quality_gate import build_review_report, decide_publication

LOGGER = logging.getLogger("funny_tutor.review_gate")


def evaluate_review_file(input_path: Path, output_path: Path) -> dict[str, Any]:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("Review input must be a JSON object")

    question_id = raw.get("question_id")
    canonical_answer = raw.get("canonical_answer")
    reviews = raw.get("reviews")
    if not isinstance(question_id, str) or not question_id.strip():
        raise ValueError("question_id must be a non-empty string")
    if not isinstance(canonical_answer, list) or not all(
        isinstance(item, str) for item in canonical_answer
    ):
        raise ValueError("canonical_answer must be a list of strings")
    if not isinstance(reviews, list):
        raise TypeError("reviews must be a JSON array")

    reports = []
    for index, item in enumerate(reviews):
        if not isinstance(item, dict):
            raise TypeError(f"reviews[{index}] must be an object")
        model = item.get("reviewer_model")
        answer = item.get("independent_answer")
        review = item.get("review")
        if not isinstance(model, str) or not model.strip():
            raise ValueError(f"reviews[{index}].reviewer_model must be non-empty")
        if not isinstance(answer, list) or not all(isinstance(v, str) for v in answer):
            raise ValueError(f"reviews[{index}].independent_answer must be string array")
        if not isinstance(review, dict):
            raise TypeError(f"reviews[{index}].review must be an object")
        reports.append(build_review_report(
            question_id=question_id,
            reviewer_model=model,
            independent_answer=answer,
            canonical_answer=canonical_answer,
            review_payload=review,
        ))

    decision = decide_publication(
        question_id=question_id,
        canonical_answer=canonical_answer,
        reports=reports,
        minimum_reviewers=2,
    )
    result = {
        "decision": decision.model_dump(mode="json"),
        "reports": [report.model_dump(mode="json") for report in reports],
        "limitations": [
            "This decision is based on supplied model-review evidence and deterministic policy.",
            "Model agreement is not proof of absolute correctness.",
            "Reviewer independence depends on actual execution/configuration; model names alone cannot prove independence.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Structured review input JSON")
    parser.add_argument("--output", type=Path, required=True, help="Decision evidence JSON output")
    args = parser.parse_args()
    result = evaluate_review_file(args.input, args.output)
    print(json.dumps(result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
