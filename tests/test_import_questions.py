"""Tests for legacy-to-canonical question import."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.import_questions import PROJECT_ROOT, convert_file, convert_legacy_question


def legacy_question() -> dict:
    return {
        "year": "2010",
        "category": "（全国卷ⅱ）",
        "question": r"题干保留 $E=BLv$。\nA. 选项一\nB. 选项二",
        "answer": ["B"],
        "analysis": r"官方解析保留 $E=BLv$。",
        "index": 1,
        "score": 6,
    }


def test_convert_legacy_question_maps_fields_and_flags_unknown_annotations() -> None:
    source = legacy_question()
    converted = convert_legacy_question(source)

    assert converted["year"] == "2010"
    assert converted["paper"] == "（全国卷ⅱ）"
    assert converted["subject"] == "physics"
    assert converted["question_raw"] == source["question"]
    assert converted["analysis_official"] == source["analysis"]
    assert converted["answer"] == ["B"]
    assert converted["id"].startswith("em-2010-1-")
    assert converted["knowledge_main"] == "待标注"
    assert converted["knowledge_tree_path"] == ["待标注"]
    assert converted["difficulty"] == 3
    assert {"待知识标注", "待难度评估", "待题型确认"} <= set(converted["exam_tags"])


def test_conversion_id_is_deterministic() -> None:
    source = legacy_question()
    assert convert_legacy_question(source)["id"] == convert_legacy_question(source)["id"]


def test_convert_file_writes_pydantic_validated_canonical_json(tmp_path: Path) -> None:
    input_path = tmp_path / "legacy.json"
    output_path = tmp_path / "canonical" / "questions.json"
    input_path.write_text(json.dumps([legacy_question()], ensure_ascii=False), encoding="utf-8")

    report = convert_file(input_path, output_path)

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["id"] == convert_legacy_question(legacy_question())["id"]
    assert report == {
        "total": 1,
        "needs_knowledge_annotation": 1,
        "needs_difficulty_review": 1,
        "needs_question_type_review": 1,
    }


def test_convert_file_rejects_missing_source_fields_without_output(tmp_path: Path) -> None:
    input_path = tmp_path / "legacy.json"
    output_path = tmp_path / "canonical.json"
    input_path.write_text(json.dumps([{"year": "2010"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="Legacy record missing fields"):
        convert_file(input_path, output_path)

    assert not output_path.exists()


def test_convert_file_rejects_non_array_source(tmp_path: Path) -> None:
    input_path = tmp_path / "legacy.json"
    input_path.write_text(json.dumps({"year": "2010"}), encoding="utf-8")

    with pytest.raises(TypeError, match="JSON array"):
        convert_file(input_path, tmp_path / "canonical.json")

def test_repository_legacy_fixture_converts_to_canonical_schema(tmp_path: Path) -> None:
    source_path = PROJECT_ROOT / "data" / "questions_em.json"
    output_path = tmp_path / "questions_em_canonical.json"

    report = convert_file(source_path, output_path)

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["total"] == len(saved)
    assert report["total"] > 0
    assert len({item["id"] for item in saved}) == len(saved)
    assert all(item["question_raw"] and item["analysis_official"] for item in saved)

