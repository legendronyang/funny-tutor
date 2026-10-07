"""Pydantic models for the Funny Tutor canonical question data.

The schema is intentionally strict about JSON value types so malformed input is
rejected at the project boundary instead of being silently coerced.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgePoint(BaseModel):
    """A single knowledge point attached to an EM question."""

    model_config = ConfigDict(strict=True)

    id: str
    name: str
    summary_plain: str
    prerequisites: list[str] = Field(default_factory=list)
    typical_pitfalls: list[str] = Field(default_factory=list)


class EMQuestion(BaseModel):
    """Canonical representation of one electromagnetism question."""

    model_config = ConfigDict(strict=True)

    id: str
    year: str
    paper: str
    subject: str
    index: int
    score: int
    question_type: str
    question_raw: str
    options: list[dict[str, Any]] | None = None
    answer: list[str]
    analysis_official: str
    images_paths: list[str] = Field(default_factory=list)
    knowledge_main: str
    knowledge_tree_path: list[str]
    knowledge_points: list[KnowledgePoint]
    exam_tags: list[str] = Field(default_factory=list)
    difficulty: int = Field(ge=1, le=5)
    memory_aids: list[str] = Field(default_factory=list)
    funny_quick_tip: str | None = None
    common_misconceptions: list[str] = Field(default_factory=list)
