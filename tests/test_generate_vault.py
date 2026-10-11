"""Tests for the end-to-end Vault generation pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.generate_vault import generate_vault


def canonical_question(question_id: str, knowledge_path: list[str], image: str | None = None) -> dict:
    return {
        "id": question_id,
        "year": "2026",
        "paper": "mock",
        "subject": "physics",
        "index": 1,
        "score": 6,
        "question_type": "single_choice",
        "question_raw": r"已知 $E=BLv$。",
        "options": [{"label": "A", "text": "正确"}, {"label": "B", "text": "错误"}],
        "answer": ["A"],
        "analysis_official": r"由 $E=BLv$ 可得答案。",
        "images_paths": [image] if image else [],
        "knowledge_main": knowledge_path[-1],
        "knowledge_tree_path": knowledge_path,
        "knowledge_points": [
            {
                "id": "kp-1",
                "name": knowledge_path[-1],
                "summary_plain": "summary",
            }
        ],
        "exam_tags": ["高中物理/电磁学"],
        "difficulty": 2,
        "memory_aids": [],
        "funny_quick_tip": None,
        "common_misconceptions": [],
    }


def write_fixture(tmp_path: Path, questions: list[dict]) -> Path:
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    return path


def write_config(tmp_path: Path, questions_path: Path, assets_dir: Path, vault_dir: Path) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(
        f"""
[llm]
model = "mock/model"
api_base = "http://mock"
timeout = 10
think_generate = false
think_verify = true

[paths]
questions_json = "{questions_path.as_posix()}"
assets_dir = "{assets_dir.as_posix()}"
vault_dir = "{vault_dir.as_posix()}"

[daily]
count = 3
""".strip(),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> Mock:
    client = Mock()
    client.complete_json.return_value = {
        "funny_explanation": "这题先看关系式。",
        "memory_aids": ["先看公式，再看方向。"],
        "common_misconceptions": ["把电场强度和电势混为一谈。"],
    }
    monkeypatch.setattr("src.generate_vault.LLMClient", lambda config, prompt: client)
    monkeypatch.setattr(
        "src.generate_vault.load_system_prompt",
        lambda path: "test prompt",
    )
    return client


def test_pipeline_generates_cards_and_syncs_assets(
    tmp_path: Path,
    fake_client: Mock,
) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "diagram.png").write_bytes(b"png")
    questions = [
        canonical_question("q1", ["磁与电磁感应", "电磁感应"], "diagram.png"),
        canonical_question("q2", ["磁与电磁感应", "电磁感应"]),
        canonical_question("q3", ["交变电流与电磁波", "电磁波"]),
    ]
    questions_path = write_fixture(tmp_path, questions)
    vault = tmp_path / "vault"
    config = write_config(tmp_path, questions_path, assets, vault)

    stats = generate_vault(config_path=config)

    assert stats == {"total": 3, "generated": 3, "skipped": 0, "failed": 0}
    assert (vault / "assets" / "diagram.png").read_bytes() == b"png"
    assert (vault / "磁与电磁感应" / "电磁感应" / "q1.md").exists()
    assert (vault / "交变电流与电磁波" / "电磁波" / "q3.md").exists()
    assert (vault / "00_今日电磁学吐槽.md").exists()
    assert fake_client.complete_json.call_count == 3

    card = (vault / "磁与电磁感应" / "电磁感应" / "q1.md").read_text(encoding="utf-8")
    assert "![](../../assets/diagram.png)" in card
    assert "$E=BLv$" in card


def test_incremental_run_skips_existing_cards_without_llm(
    tmp_path: Path,
    fake_client: Mock,
) -> None:
    questions = [canonical_question("q1", ["磁与电磁感应", "电磁感应"])]
    questions_path = write_fixture(tmp_path, questions)
    vault = tmp_path / "vault"
    config = write_config(tmp_path, questions_path, tmp_path / "assets", vault)

    first = generate_vault(config_path=config)
    assert first["generated"] == 1
    fake_client.reset_mock()

    second = generate_vault(config_path=config)
    assert second["generated"] == 0
    assert second["skipped"] == 1
    fake_client.complete_json.assert_not_called()


def test_force_regenerates_existing_card(
    tmp_path: Path,
    fake_client: Mock,
) -> None:
    questions = [canonical_question("q1", ["磁与电磁感应", "电磁感应"])]
    questions_path = write_fixture(tmp_path, questions)
    vault = tmp_path / "vault"
    config = write_config(tmp_path, questions_path, tmp_path / "assets", vault)

    generate_vault(config_path=config)
    fake_client.reset_mock()

    stats = generate_vault(config_path=config, force=True)

    assert stats["generated"] == 1
    fake_client.complete_json.assert_called_once()


def test_llm_failure_skips_one_question_and_continues(
    tmp_path: Path,
    fake_client: Mock,
) -> None:
    questions = [
        canonical_question("q1", ["磁与电磁感应", "电磁感应"]),
        canonical_question("q2", ["磁与电磁感应", "磁场基础"]),
    ]
    questions_path = write_fixture(tmp_path, questions)
    vault = tmp_path / "vault"
    config = write_config(tmp_path, questions_path, tmp_path / "assets", vault)

    fake_client.complete_json.side_effect = [
        RuntimeError("bad JSON"),
        {
            "funny_explanation": "ok",
            "memory_aids": ["先找受力关系。"],
            "common_misconceptions": ["忽略方向判断。"],
        },
    ]

    stats = generate_vault(config_path=config)

    assert stats["failed"] == 1
    assert stats["generated"] == 1
    assert (vault / "磁与电磁感应" / "磁场基础" / "q2.md").exists()
    assert (vault / "00_今日电磁学吐槽.md").exists()


def test_force_failure_archives_old_card_and_excludes_it_from_dashboard(
    tmp_path: Path,
    fake_client: Mock,
) -> None:
    questions = [
        canonical_question("q1", ["磁与电磁感应", "电磁感应"]),
        canonical_question("q2", ["磁与电磁感应", "磁场基础"]),
    ]
    questions_path = write_fixture(tmp_path, questions)
    vault = tmp_path / "vault"
    config = write_config(tmp_path, questions_path, tmp_path / "assets", vault)

    stale_card = vault / "磁与电磁感应" / "电磁感应" / "q1.md"
    stale_card.parent.mkdir(parents=True, exist_ok=True)
    stale_card.write_text("# Stale candidate", encoding="utf-8")
    fake_client.complete_json.side_effect = [
        RuntimeError("decoded control characters"),
        {
            "funny_explanation": "本题先检查物理关系。",
            "memory_aids": ["先列关系式。"],
            "common_misconceptions": ["注意单位。"],
        },
    ]

    stats = generate_vault(config_path=config, force=True)

    assert stats == {"total": 2, "generated": 1, "skipped": 0, "failed": 1}
    assert not stale_card.exists()
    archived = vault / ".stale_candidates" / "磁与电磁感应" / "电磁感应" / "q1.md"
    assert archived.read_text(encoding="utf-8") == "# Stale candidate"
    dashboard = (vault / "00_今日电磁学吐槽.md").read_text(encoding="utf-8")
    assert "[[q1]]" not in dashboard
    assert "[[q2]]" in dashboard


def test_dry_run_validates_without_llm_or_writes(
    tmp_path: Path,
    fake_client: Mock,
) -> None:
    questions = [canonical_question("q1", ["磁与电磁感应", "电磁感应"])]
    questions_path = write_fixture(tmp_path, questions)
    vault = tmp_path / "vault"
    config = write_config(tmp_path, questions_path, tmp_path / "assets", vault)

    stats = generate_vault(config_path=config, dry_run=True)

    assert stats == {"total": 1, "generated": 0, "skipped": 0, "failed": 0}
    assert not vault.exists()
    fake_client.complete_json.assert_not_called()


def test_invalid_generate_payload_is_not_written(
    tmp_path: Path,
    fake_client: Mock,
) -> None:
    questions = [canonical_question("q1", ["磁与电磁感应", "电磁感应"])]
    questions_path = write_fixture(tmp_path, questions)
    vault = tmp_path / "vault"
    config = write_config(tmp_path, questions_path, tmp_path / "assets", vault)

    fake_client.complete_json.return_value = {
        "knowledge_main": "越界字段",
        "memory_aids": [{"title": "也不允许"}],
    }

    stats = generate_vault(config_path=config)

    assert stats == {"total": 1, "generated": 0, "skipped": 0, "failed": 1}
    assert not (vault / "磁与电磁感应" / "电磁感应" / "q1.md").exists()
    assert (vault / "00_今日电磁学吐槽.md").exists()
