"""Convert the legacy OCR question fixture into the canonical EMQuestion format.

This is a deterministic source adapter, not a knowledge-labeling system. Missing
annotations are marked explicitly as pending review rather than guessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

try:
    from .schema import EMQuestion
except ImportError:  # pragma: no cover - supports direct script execution
    from schema import EMQuestion

LOGGER = logging.getLogger("funny_tutor.import_questions")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _stable_id(item: dict[str, Any]) -> str:
    identity = "\\0".join(
        str(item.get(key, "")) for key in ("year", "category", "index", "question")
    )
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:10]
    year = re.sub(r"[^0-9]", "", str(item.get("year", ""))) or "unknown"
    index = item.get("index", "x")
    return f"em-{year}-{index}-{digest}"


def convert_legacy_question(item: dict[str, Any]) -> dict[str, Any]:
    """Map one legacy record; clearly flag fields that need human annotation."""
    required = ("year", "category", "question", "answer", "analysis", "index", "score")
    missing = [key for key in required if key not in item]
    if missing:
        raise ValueError(f"Legacy record missing fields: {', '.join(missing)}")

    year = str(item["year"]).strip()
    paper = str(item["category"]).strip()
    question_raw = item["question"]
    if not isinstance(question_raw, str) or not question_raw.strip():
        raise ValueError("Legacy question must contain non-empty question text")
    answer = item["answer"]
    if isinstance(answer, str):
        answer = [answer]
    if not isinstance(answer, list) or not all(isinstance(value, str) for value in answer):
        raise ValueError("Legacy answer must be a string or a list of strings")

    return {
        "id": _stable_id(item),
        "year": year,
        "paper": paper,
        "subject": "physics",
        "index": int(item["index"]),
        "score": int(item["score"]),
        "question_type": "unknown",
        "question_raw": question_raw,
        "options": None,
        "answer": answer,
        "analysis_official": str(item["analysis"]),
        "images_paths": item.get("images_paths", []),
        "knowledge_main": "待标注",
        "knowledge_tree_path": ["待标注"],
        "knowledge_points": [{
            "id": "knowledge-pending",
            "name": "待标注",
            "summary_plain": "导入占位符：请人工确认知识点后替换。",
        }],
        "exam_tags": ["来源导入", "待知识标注", "待难度评估", "待题型确认"],
        "difficulty": 3,
        "memory_aids": [],
        "funny_quick_tip": None,
        "common_misconceptions": [],
    }


def convert_file(input_path: Path, output_path: Path) -> dict[str, int]:
    """Convert legacy JSON into validated canonical JSON and report placeholders."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError("Legacy question source must be a JSON array")

    converted = [convert_legacy_question(item) for item in raw]
    # Validate the complete output before writing anything.
    validated = [EMQuestion.model_validate(item) for item in converted]
    ids = [question.id for question in validated]
    if len(ids) != len(set(ids)):
        raise ValueError("Generated question IDs are not unique")

    report = {
        "total": len(validated),
        "needs_knowledge_annotation": len(validated),
        "needs_difficulty_review": len(validated),
        "needs_question_type_review": len(validated),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([question.model_dump(mode="json") for question in validated],
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert legacy OCR questions to the canonical EMQuestion schema"
    )
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data/questions_em.json")
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT_ROOT / "data/questions_em_canonical.json",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args()
    report = convert_file(args.input, args.output)
    LOGGER.info("Canonical import written to %s", args.output)
    LOGGER.info("Import report: %s", json.dumps(report, ensure_ascii=False))
    LOGGER.warning(
        "Imported records use explicit placeholders for knowledge, difficulty, and question type; review before treating them as curated data."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
