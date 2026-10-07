"""End-to-end Funny Tutor Vault generation pipeline.

The pipeline validates the canonical question bank first, synchronizes assets,
incrementally generates Funny Tutor payloads, renders Obsidian cards, and
rebuilds the daily dashboard.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

try:
    from .daily_index import build_daily_index
    from .llm_client import LLMClient, decide_field_mode, load_llm_config, load_system_prompt
    from .markdown_renderer import render_question_card
    from .schema import EMQuestion
except ImportError:  # pragma: no cover - supports direct script execution
    from daily_index import build_daily_index
    from llm_client import LLMClient, decide_field_mode, load_llm_config, load_system_prompt
    from markdown_renderer import render_question_card
    from schema import EMQuestion

LOGGER = logging.getLogger("funny_tutor.pipeline")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = PROJECT_ROOT / "src" / "prompts" / "funny_tutor_em.txt"


def _load_questions(path: Path) -> list[EMQuestion]:
    """Load and validate the canonical question bank before processing."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Question bank must be a JSON array")
    return [EMQuestion.model_validate(item) for item in raw]


def _sync_assets(source: Path, destination: Path) -> None:
    """Mirror the source asset tree into the Vault asset directory."""
    if not source.exists():
        LOGGER.info("Asset source does not exist; skipping asset sync: %s", source)
        return
    if not source.is_dir():
        raise ValueError(f"Asset source is not a directory: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)


def _question_path(vault_dir: Path, question: EMQuestion) -> Path:
    """Return the deterministic Markdown path for one question."""
    relative_parts = [part.strip() for part in question.knowledge_tree_path if part.strip()]
    if not relative_parts:
        raise ValueError(f"Question {question.id} has an empty knowledge_tree_path")
    return vault_dir.joinpath(*relative_parts, f"{question.id}.md")


def _question_prompt(question: EMQuestion) -> str:
    """Build the provider-neutral Funny Tutor generation/verification prompt."""
    context: dict[str, Any] = {
        "id": question.id,
        "question_raw": question.question_raw,
        "options": question.options,
        "answer": question.answer,
        "analysis_official": question.analysis_official,
        "knowledge_main": question.knowledge_main,
        "knowledge_tree_path": question.knowledge_tree_path,
        "knowledge_points": [point.model_dump(mode="json") for point in question.knowledge_points],
        "memory_aids": question.memory_aids,
        "funny_quick_tip": question.funny_quick_tip,
        "common_misconceptions": question.common_misconceptions,
    }
    return (
        "Create the Funny Tutor payload for this canonical question. "
        "Return only the JSON object with keys funny_explanation, memory_aids, "
        "common_misconceptions. Preserve all formulas and physical symbols exactly "
        "as supplied; do not solve or rewrite the official quantitative analysis.

"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )


def _merge_payload(question: EMQuestion, payload: dict[str, Any]) -> dict[str, Any]:
    """Use LLM fields when present and canonical fields as safe fallbacks."""
    merged: dict[str, Any] = {
        "funny_quick_tip": question.funny_quick_tip,
        "memory_aids": question.memory_aids,
        "common_misconceptions": question.common_misconceptions,
    }
    merged.update(payload)
    return merged


def generate_vault(
    *,
    config_path: Path,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Build the Vault and return counters for processed/skipped/failed cards."""
    import tomllib

    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    paths = config.get("paths", {})
    questions_path = PROJECT_ROOT / paths.get("questions_json", "data/questions_em.json")
    assets_dir = PROJECT_ROOT / paths.get("assets_dir", "data/assets")
    vault_dir = PROJECT_ROOT / paths.get("vault_dir", "vault/FunnyTutor_EM_Vault")
    daily_count = int(config.get("daily", {}).get("count", 3))

    questions = _load_questions(questions_path)
    question_ids = [question.id for question in questions]

    if dry_run:
        return {"total": len(questions), "generated": 0, "skipped": 0, "failed": 0}

    vault_dir.mkdir(parents=True, exist_ok=True)
    _sync_assets(assets_dir, vault_dir / "assets")

    llm_config = load_llm_config(config_path)
    client = LLMClient(llm_config, load_system_prompt(PROMPT_PATH))

    generated = 0
    skipped = 0
    failed = 0

    for question in questions:
        target = _question_path(vault_dir, question)
        if target.exists() and not force:
            LOGGER.info("SKIP %s: Markdown card already exists", question.id)
            skipped += 1
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "generate"
        for value in (
            question.memory_aids,
            question.funny_quick_tip,
            question.common_misconceptions,
        ):
            if decide_field_mode(value) == "verify":
                mode = "verify"
                break

        try:
            payload = client.complete_json(
                question_id=question.id,
                user_prompt=_question_prompt(question),
                mode=mode,
            )
            asset_relative_path = Path(
                os.path.relpath(vault_dir / "assets", target.parent)
            ).as_posix()
            markdown = render_question_card(
                question,
                _merge_payload(question, payload),
                asset_relative_path=asset_relative_path,
            )
            target.write_text(markdown, encoding="utf-8")
            generated += 1
            LOGGER.info("GENERATED %s -> %s", question.id, target)
        except Exception as exc:
            failed += 1
            LOGGER.exception("SKIP %s: LLM/rendering failed: %s", question.id, exc)
            continue

    dashboard = vault_dir / "00_今日电磁学吐槽.md"
    dashboard.write_text(
        build_daily_index(question_ids, daily_count, title="## 今日电磁学吐槽"),
        encoding="utf-8",
    )
    return {
        "total": len(questions),
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the Funny Tutor Obsidian Vault")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "config.toml")
    parser.add_argument("--force", action="store_true", help="Regenerate existing question cards")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the question bank and paths without calling the LLM or writing files",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args()
    stats = generate_vault(
        config_path=args.config,
        force=args.force,
        dry_run=args.dry_run,
    )
    LOGGER.info(
        "Done: total=%d generated=%d skipped=%d failed=%d",
        stats["total"],
        stats["generated"],
        stats["skipped"],
        stats["failed"],
    )
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
