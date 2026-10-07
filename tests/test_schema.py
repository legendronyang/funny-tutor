"""Tests for the canonical Funny Tutor question schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schema import EMQuestion


def valid_question() -> dict:
    return {
        "id": "em-2026-001",
        "year": "2026",
        "paper": "mock-paper",
        "subject": "physics",
        "index": 1,
        "score": 6,
        "question_type": "single_choice",
        "question_raw": r"已知 $E = BLv$。",
        "options": [
            {"label": "A", "text": "正确"},
            {"label": "B", "text": "错误"},
        ],
        "answer": ["A"],
        "analysis_official": r"由法拉第定律可得 $E = BLv$。",
        "images_paths": ["em_diagrams/q1.png"],
        "knowledge_main": "磁与电磁感应",
        "knowledge_tree_path": [
            "磁与电磁感应",
            "电磁感应",
            "感应电动势与法拉第定律",
        ],
        "knowledge_points": [
            {
                "id": "emf-faraday",
                "name": "感应电动势与法拉第定律",
                "summary_plain": "磁通量变化产生感应电动势。",
                "prerequisites": ["磁通量"],
                "typical_pitfalls": ["把磁通量大小等同于磁通量变化率"],
            }
        ],
        "exam_tags": ["高中物理/电磁学", "真题/选择题"],
        "difficulty": 3,
        "memory_aids": ["磁通量变，电动势来上班。"],
        "funny_quick_tip": "先看磁通量有没有变化。",
        "common_misconceptions": ["只看磁场强弱，不看磁通量变化。"],
    }


def test_valid_question_is_accepted() -> None:
    question = EMQuestion.model_validate(valid_question())

    assert question.id == "em-2026-001"
    assert question.knowledge_points[0].id == "emf-faraday"
    assert question.difficulty == 3


@pytest.mark.parametrize(
    "field",
    ["id", "year", "paper", "subject", "question_raw", "answer", "analysis_official"],
)
def test_missing_required_field_is_rejected(field: str) -> None:
    payload = valid_question()
    payload.pop(field)

    with pytest.raises(ValidationError):
        EMQuestion.model_validate(payload)


def test_wrong_scalar_type_is_rejected() -> None:
    payload = valid_question()
    payload["index"] = "1"

    with pytest.raises(ValidationError):
        EMQuestion.model_validate(payload)


def test_wrong_nested_type_is_rejected() -> None:
    payload = valid_question()
    payload["knowledge_points"][0]["prerequisites"] = "magnetic flux"

    with pytest.raises(ValidationError):
        EMQuestion.model_validate(payload)


def test_difficulty_must_be_between_one_and_five() -> None:
    payload = valid_question()
    payload["difficulty"] = 6

    with pytest.raises(ValidationError):
        EMQuestion.model_validate(payload)

