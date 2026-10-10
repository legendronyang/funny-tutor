"""Pydantic models for the Funny Tutor canonical question data.

The schema is intentionally strict about JSON value types so malformed input is
rejected at the project boundary instead of being silently coerced.
"""

from __future__ import annotations

from typing import Any, Literal

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



ReviewStatus = Literal["PASS", "FAIL", "UNCERTAIN"]
PublicationStatus = Literal["ACCEPT", "REVIEW", "REJECT"]
AnswerMatchStatus = Literal["MATCH", "MISMATCH", "UNCERTAIN"]


class ReviewCheck(BaseModel):
    """One auditable content-review result; PASS requires concrete evidence."""

    model_config = ConfigDict(strict=True, extra="forbid")

    status: ReviewStatus
    evidence: list[str] = Field(min_length=1)
    issues: list[str] = Field(default_factory=list)


class IndependentSolutionPayload(BaseModel):
    """A reviewer model's first-pass solution before seeing the reference answer."""

    model_config = ConfigDict(strict=True, extra="forbid")

    answer: list[str] = Field(min_length=1)
    reasoning: list[str] = Field(min_length=1)
    uncertainties: list[str] = Field(default_factory=list)


class ReviewReportPayload(BaseModel):
    """Structured review of a candidate, after an independent first-pass solution."""

    model_config = ConfigDict(strict=True, extra="forbid")

    answer_correctness: ReviewCheck
    physics_reasoning: ReviewCheck
    formula_units: ReviewCheck
    numerical_consistency: ReviewCheck
    student_clarity: ReviewCheck
    latex_integrity: ReviewCheck
    issues: list[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    """Auditable review report enriched by the application, not by model assertions."""

    model_config = ConfigDict(strict=True, extra="forbid")

    question_id: str
    reviewer_model: str
    independent_answer: list[str] = Field(min_length=1)
    canonical_answer_match: AnswerMatchStatus
    answer_correctness: ReviewCheck
    physics_reasoning: ReviewCheck
    formula_units: ReviewCheck
    numerical_consistency: ReviewCheck
    student_clarity: ReviewCheck
    latex_integrity: ReviewCheck
    issues: list[str] = Field(default_factory=list)


class PublicationDecision(BaseModel):
    """Final deterministic release decision; model confidence is not a release input."""

    model_config = ConfigDict(strict=True, extra="forbid")

    question_id: str
    decision: PublicationStatus
    distinct_reviewers: int = Field(ge=0)
    reasons: list[str] = Field(min_length=1)
    compared_answer: list[str] = Field(default_factory=list)
