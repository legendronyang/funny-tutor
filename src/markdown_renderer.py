"""Pure Markdown renderer for Funny Tutor Obsidian question cards."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any

from .schema import EMQuestion


def _clean_asset_path(path: str) -> str:
    """Normalize an asset path and reject paths that escape the asset root."""
    normalized = path.replace("\\", "/").strip()
    if not normalized:
        raise ValueError("images_paths cannot contain an empty path")
    if normalized.startswith("/"):
        raise ValueError(f"Asset path must be relative: {path!r}")

    parts = [part for part in PurePosixPath(normalized).parts if part not in ("", ".")]
    if not parts:
        raise ValueError(f"Asset path is empty after normalization: {path!r}")

    # Source data may store paths relative to either the project root or assets/.
    while parts[:2] == ["data", "assets"]:
        parts = parts[2:]
    if parts and parts[0] == "assets":
        parts = parts[1:]

    if not parts or ".." in parts:
        raise ValueError(f"Asset path escapes the assets root: {path!r}")

    return "/".join(parts)


def render_asset_links(
    images_paths: Sequence[str],
    *,
    asset_relative_path: str = "../../assets",
) -> str:
    """Render image references relative to the current question-card directory."""
    if not images_paths:
        return ""

    prefix = asset_relative_path.replace("\\", "/").rstrip("/")
    if not prefix:
        raise ValueError("asset_relative_path cannot be empty")
    if prefix.startswith("/"):
        raise ValueError("asset_relative_path must be relative")

    links = [
        f"![]({prefix}/{_clean_asset_path(image_path)})"
        for image_path in images_paths
    ]
    return "\n".join(links)


def _render_options(options: Sequence[Mapping[str, Any]] | None) -> str:
    if not options:
        return ""

    lines: list[str] = []
    for option in options:
        label = option.get("label", option.get("key", option.get("option")))
        text = option.get("text", option.get("content", option.get("value")))

        if label is not None and text is not None:
            lines.append(f"- {label}. {text}")
        else:
            lines.append(
                f"- {json.dumps(dict(option), ensure_ascii=False, sort_keys=True)}"
            )
    return "\n".join(lines)


def _render_bullets(items: Sequence[str] | None) -> str:
    if not items:
        return ""
    return "\n".join(f"- {item}" for item in items)


def _render_tip_callout(payload: Mapping[str, Any]) -> str:
    sections: list[str] = []

    explanation = payload.get("funny_explanation")
    if isinstance(explanation, str) and explanation.strip():
        sections.append(explanation.strip())

    quick_tip = payload.get("funny_quick_tip")
    if isinstance(quick_tip, str) and quick_tip.strip():
        sections.append(f"**快速记忆：** {quick_tip.strip()}")

    memory_aids = payload.get("memory_aids")
    if isinstance(memory_aids, Sequence) and not isinstance(memory_aids, (str, bytes)):
        aids = [str(item).strip() for item in memory_aids if str(item).strip()]
        if aids:
            sections.append(_render_bullets(aids))

    if not sections:
        return ""

    body = "\n\n".join(sections)
    callout_lines = ["> [!tip] Funny Tutor"]
    callout_lines.extend(f"> {line}" if line else ">" for line in body.splitlines())
    return "\n".join(callout_lines)


def _render_warning_callout(payload: Mapping[str, Any]) -> str:
    misconceptions = payload.get("common_misconceptions")
    if not isinstance(misconceptions, Sequence) or isinstance(
        misconceptions, (str, bytes)
    ):
        return ""

    items = [str(item).strip() for item in misconceptions if str(item).strip()]
    if not items:
        return ""

    lines = ["> [!warning] 翻车点"]
    lines.extend(f"> - {item}" for item in items)
    return "\n".join(lines)


def _render_tags(question: EMQuestion) -> str:
    tags: list[str] = [
        "#高中物理/电磁学",
        f"#真题/{question.question_type}",
    ]
    for tag in question.exam_tags:
        normalized = str(tag).strip()
        if normalized and not normalized.startswith("#"):
            normalized = f"#{normalized}"
        if normalized and normalized not in tags:
            tags.append(normalized)
    return " ".join(tags)


def _render_knowledge_links(question: EMQuestion) -> str:
    main = question.knowledge_main.strip()
    path = [item.strip() for item in question.knowledge_tree_path if item.strip()]

    lines: list[str] = []
    if main:
        lines.append(f"主知识点：[[{main}]]")

    if path:
        breadcrumb = " → ".join(f"[[{item}]]" for item in path)
        lines.append(f"知识树：{breadcrumb}")

    return "\n".join(lines)


def render_question_card(
    question: EMQuestion,
    llm_payload: Mapping[str, Any] | None = None,
    *,
    asset_relative_path: str = "../../assets",
) -> str:
    """Return one complete Obsidian Markdown question card.

    The renderer is pure: it does not call an LLM and does not write files.
    Canonical question/analysis text is inserted without transformation.
    """
    payload = llm_payload or {}

    title = (
        f"# [{question.year} {question.paper} 第{question.index}题] "
        f"{question.knowledge_main}"
    )

    sections: list[str] = [
        title,
        "",
        _render_tags(question),
        "",
        "## 原题",
        question.question_raw,
    ]

    options = _render_options(question.options)
    if options:
        sections.extend(["", "### 选项", options])

    images = render_asset_links(
        question.images_paths,
        asset_relative_path=asset_relative_path,
    )
    if images:
        sections.extend(["", "### 图片", images])

    sections.extend(
        [
            "",
            "## 参考答案",
            ", ".join(question.answer),
            "",
            "## 官方解析",
            question.analysis_official,
        ]
    )

    tip_callout = _render_tip_callout(payload)
    if tip_callout:
        sections.extend(["", tip_callout])

    warning_callout = _render_warning_callout(payload)
    if warning_callout:
        sections.extend(["", warning_callout])

    knowledge_links = _render_knowledge_links(question)
    if knowledge_links:
        sections.extend(["", "## 知识树", knowledge_links])

    sections.extend(
        [
            "",
            f"难度：{question.difficulty}/5",
            f"题型：{question.question_type}",
            "",
        ]
    )

    return "\n".join(sections)


__all__ = ["render_asset_links", "render_question_card"]
