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
    evidence: dict[str, Any] = json.loads(decision_file.read_text(encoding="utf-8"))
    decision = evidence.get("decision", {})
    if decision.get("question_id") != question_id:
        raise ValueError("Decision evidence question_id does not match requested question")
    if decision.get("decision") != "ACCEPT":
        raise ValueError(
            f"Publication blocked: decision is {decision.get('decision')!r}, not 'ACCEPT'"
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
