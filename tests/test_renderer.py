"""Tests for the pure Obsidian Markdown renderer."""

from __future__ import annotations

from src.markdown_renderer import render_asset_links, render_question_card
from src.schema import EMQuestion


def make_question(**overrides) -> EMQuestion:
    data = {
        "id": "em-2018-001",
        "year": "2018",
        "paper": "全国一卷",
        "subject": "physics",
        "index": 12,
        "score": 6,
        "question_type": "single_choice",
        "question_raw": (
            "线圈中的磁通量为 $\\Phi=BS\\cos\\theta$。"
            "已知 $B=2\\mathrm{T}$。"
        ),
        "options": [
            {"label": "A", "text": "$1 \\mathrm{V}$"},
            {"label": "B", "text": "$2 \\mathrm{V}$"},
        ],
        "answer": ["B"],
        "analysis_official": (
            "根据法拉第电磁感应定律，$E=-\\frac{\\Delta\\Phi}{\\Delta t}$。"
        ),
        "images_paths": ["em_diagrams/coil.png"],
        "knowledge_main": "法拉第电磁感应定律",
        "knowledge_tree_path": [
            "磁与电磁感应",
            "电磁感应",
            "感应电动势与法拉第定律",
        ],
        "knowledge_points": [
            {
                "id": "kp-001",
                "name": "感应电动势",
                "summary_plain": "磁通量变化产生感应电动势。",
            }
        ],
        "exam_tags": ["真题", "电磁感应"],
        "difficulty": 3,
    }
    data.update(overrides)
    return EMQuestion.model_validate(data)


def test_render_question_card_contains_expected_sections() -> None:
    question = make_question()
    payload = {
        "funny_explanation": "磁通量一变，线圈就开始“报警”。",
        "memory_aids": ["磁通量变 → 有感应"],
        "common_misconceptions": ["只看到 B 不看磁通量变化。"],
    }

    markdown = render_question_card(
        question,
        payload,
        asset_relative_path="../../../assets",
    )

    assert "# [2018 全国一卷 第12题] 法拉第电磁感应定律" in markdown
    assert "## 原题" in markdown
    assert "## 参考答案\nB" in markdown
    assert "## 官方解析" in markdown
    assert "> [!tip] Funny Tutor" in markdown
    assert "> [!warning] 翻车点" in markdown
    assert "[[磁与电磁感应]]" in markdown
    assert "[[电磁感应]]" in markdown
    assert "[[感应电动势与法拉第定律]]" in markdown
    assert "#高中物理/电磁学" in markdown
    assert "#真题/single_choice" in markdown
    assert "![](../../../assets/em_diagrams/coil.png)" in markdown


def test_render_preserves_latex_source_verbatim() -> None:
    question = make_question()
    markdown = render_question_card(question, {})

    assert question.question_raw in markdown
    assert question.analysis_official in markdown
    assert r"$\Phi=BS\cos\theta$" in markdown
    assert r"$E=-\frac{\Delta\Phi}{\Delta t}$" in markdown


def test_render_preserves_question_without_llm_payload() -> None:
    markdown = render_question_card(make_question())

    assert "## 原题" in markdown
    assert "## 官方解析" in markdown
    assert "> [!tip] Funny Tutor" not in markdown
    assert "> [!warning] 翻车点" not in markdown


def test_render_asset_links_normalizes_source_prefixes() -> None:
    markdown = render_asset_links(
        [
            "em_diagrams/a.png",
            "assets/em_diagrams/b.png",
            "data/assets/em_diagrams/c.png",
        ],
        asset_relative_path="../../../assets",
    )

    assert markdown == (
        "![](../../../assets/em_diagrams/a.png)\n"
        "![](../../../assets/em_diagrams/b.png)\n"
        "![](../../../assets/em_diagrams/c.png)"
    )


def test_render_rejects_absolute_asset_paths() -> None:
    import pytest

    with pytest.raises(ValueError, match="relative"):
        render_asset_links(["/tmp/a.png"])


def test_render_rejects_asset_path_traversal() -> None:
    import pytest

    with pytest.raises(ValueError, match="escapes"):
        render_asset_links(["../outside/a.png"])


def test_render_supports_quick_tip_and_flexible_option_keys() -> None:
    question = make_question(
        options=[
            {"key": "A", "content": "$3 \\mathrm{V}$"},
            {"option": "B", "value": "$4 \\mathrm{V}$"},
        ],
    )
    payload = {
        "funny_explanation": "一句解释。",
        "funny_quick_tip": "先看磁通量，再看变化。",
    }

    markdown = render_question_card(question, payload)

    assert "- A. $3 \\mathrm{V}$" in markdown
    assert "- B. $4 \\mathrm{V}$" in markdown
    assert "**快速记忆：** 先看磁通量，再看变化。" in markdown


def test_render_keeps_custom_exam_tags_without_duplicating_them() -> None:
    question = make_question(exam_tags=["真题", "#电磁感应", "#高中物理/电磁学"])

    markdown = render_question_card(question, {})

    assert markdown.count("#高中物理/电磁学") == 1
    assert "#真题" in markdown
    assert "#电磁感应" in markdown
