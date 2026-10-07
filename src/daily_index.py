"""Pure functions for selecting questions for the daily dashboard."""

from __future__ import annotations

import random
from collections.abc import Sequence
from random import Random


def _unique_ids(question_ids: Sequence[str]) -> list[str]:
    """Return non-empty question IDs once, preserving input order."""
    seen: set[str] = set()
    result: list[str] = []

    for question_id in question_ids:
        normalized = str(question_id).strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result


def select_question_ids(
    question_ids: Sequence[str],
    count: int,
    *,
    rng: Random | None = None,
) -> list[str]:
    """Randomly select up to count unique question IDs.

    If count is greater than the number of available unique IDs, all
    available IDs are returned in random order.
    """
    if count < 0:
        raise ValueError("count must be >= 0")

    candidates = _unique_ids(question_ids)
    if count == 0 or not candidates:
        return []

    picker = rng or random
    return picker.sample(candidates, min(count, len(candidates)))


def render_daily_index(
    question_ids: Sequence[str],
    *,
    title: str = "## 今日电磁学",
) -> str:
    """Render selected question IDs as an Obsidian dashboard fragment."""
    ids = _unique_ids(question_ids)
    lines = [title]
    if not ids:
        lines.append("- 今日暂无题目")
    else:
        lines.extend(f"- [[{question_id}]]" for question_id in ids)
    return "\n".join(lines)


def build_daily_index(
    question_ids: Sequence[str],
    count: int,
    *,
    rng: Random | None = None,
    title: str = "## 今日电磁学",
) -> str:
    """Select today's questions and return the dashboard Markdown fragment."""
    selected = select_question_ids(question_ids, count, rng=rng)
    return render_daily_index(selected, title=title)


__all__ = ["build_daily_index", "render_daily_index", "select_question_ids"]
