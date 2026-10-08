"""Pydantic models for the Funny Tutor canonical question data.

The schema is intentionally strict about JSON value types so malformed input is
rejected at the project boundary instead of being silently coerced.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgePoint(BaseModel):
    """A single knowledge point attached to an EM question."""

    model_config = ConfigDict(strict=True)

    id: str
    name: str
    summary_plain: str
    prerequisites: list[str] = Field(default_factory=list)
    typical_pitfalls: list[str] = Field(default_factory=list)


class FunnyTutorPayload(BaseModel):
    """Strict LLM output contract for a generated Funny Tutor card payload."""

    model_config = ConfigDict(strict=True, extra="forbid")

    funny_explanation: str
    memory_aids: list[str] = Field(min_length=1, max_length=3)
    common_misconceptions: list[str] = Field(min_length=1, max_length=3)

    @field_validator("funny_explanation")
    @classmethod
    def _explanation_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("funny_explanation must not be blank")
        return value

    @field_validator("memory_aids", "common_misconceptions")
    @classmethod
    def _items_must_not_be_blank(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("Funny Tutor list items must not be blank")
        return values


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
