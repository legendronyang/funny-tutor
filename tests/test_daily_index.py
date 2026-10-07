"""Tests for the daily question selection/dashboard helpers."""

from __future__ import annotations

import random

import pytest

from src.daily_index import (
    build_daily_index,
    render_daily_index,
    select_question_ids,
)


def test_select_question_ids_returns_requested_unique_count() -> None:
    rng = random.Random(42)

    selected = select_question_ids(
        ["q1", "q2", "q3", "q4", "q5"],
        3,
        rng=rng,
    )

    assert len(selected) == 3
    assert len(set(selected)) == 3
    assert set(selected).issubset({"q1", "q2", "q3", "q4", "q5"})


def test_select_question_ids_does_not_repeat_duplicate_input_ids() -> None:
    rng = random.Random(7)

    selected = select_question_ids(
        ["q1", "q1", "q2", "q2", "q3"],
        3,
        rng=rng,
    )

    assert len(selected) == 3
    assert len(set(selected)) == 3
    assert set(selected) == {"q1", "q2", "q3"}


def test_count_greater_than_total_returns_all_questions() -> None:
    rng = random.Random(1)

    selected = select_question_ids(["q1", "q2", "q3"], 10, rng=rng)

    assert len(selected) == 3
    assert set(selected) == {"q1", "q2", "q3"}


def test_zero_count_returns_empty_list() -> None:
    assert select_question_ids(["q1", "q2"], 0) == []


def test_negative_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="count"):
        select_question_ids(["q1"], -1)


def test_empty_question_bank_returns_empty_list() -> None:
    assert select_question_ids([], 3) == []


def test_render_daily_index_creates_obsidian_links() -> None:
    rendered = render_daily_index(
        ["2010-001", "2010-003"],
        title="## 今日电磁学吐槽",
    )

    assert rendered == (
        "## 今日电磁学吐槽\n"
        "- [[2010-001]]\n"
        "- [[2010-003]]"
    )


def test_render_daily_index_handles_empty_selection() -> None:
    assert render_daily_index([]) == "## 今日电磁学\n- 今日暂无题目"


def test_build_daily_index_selects_and_renders() -> None:
    rng = random.Random(10)

    rendered = build_daily_index(
        ["q1", "q2", "q3", "q4"],
        2,
        rng=rng,
    )

    lines = rendered.splitlines()
    assert lines[0] == "## 今日电磁学"
    assert len(lines) == 3
    assert all(line.startswith("- [[q") and line.endswith("]]") for line in lines[1:])


def test_repeated_seed_produces_reproducible_selection() -> None:
    first = select_question_ids(
        ["q1", "q2", "q3", "q4"],
        2,
        rng=random.Random(123),
    )
    second = select_question_ids(
        ["q1", "q2", "q3", "q4"],
        2,
        rng=random.Random(123),
    )

    assert first == second
