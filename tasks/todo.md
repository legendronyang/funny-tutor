# tasks/todo.md — Funny Tutor 1.0 execution checklist

Last reconciled: 2026-10-11. This file is the **current actionable checklist**. Historical Smoke Test iterations and Prompt revisions remain documented in `tasks/plan.md`; they are not a reason to continue open-ended Prompt tuning.

## 1.0 scope

1.0 targets the end-to-end **candidate generation pipeline**: source import and validation → configured LLM call → strict payload/integrity validation → Obsidian Markdown → daily dashboard → incremental rerun → explicit review/publish boundary.

It does **not** claim that every generated explanation is physically correct, that the 20-question bank is curated, or that cloud-model comparison is complete. Known defects and deferred work are in `tech-debt.md`.

## Task status summary

| Task | Status | Evidence / remaining boundary |
|---|---|---|
| Task 1 — Project skeleton and canonical schema | DONE | `src/schema.py`; schema tests; user reports Ruff and pytest pass |
| Task 2 — LiteLLM client and Generate/Verify contract | DONE for pipeline | `src/llm_client.py`; mock tests and local Qwen Verify A/B log; cloud comparison deferred |
| Task 3 — Obsidian Markdown renderer | IMPLEMENTED | `src/markdown_renderer.py`; renderer tests; manual Obsidian formula/image inspection remains |
| Task 4 — Daily dashboard selection | DONE | `src/daily_index.py`; unique selection, bounds and Markdown tests |
| Task 5 — Pipeline, assets, incremental/force behavior | IMPLEMENTED | `src/generate_vault.py`; pipeline tests; new stale-card-on-force-failure regression test needs local execution |
| Task 6 — Legacy import to Canonical JSON | DONE for current fixture | `src/import_questions.py`; prior local conversion of 10 records; annotations are explicit placeholders, not curated metadata |
| Task 7 — Strict Generate payload | DONE structurally | Pydantic + Ollama JSON Schema + control-character gate; semantic content still requires review |
| Task 8 — Evidence-based review and controlled publish | IMPLEMENTED, operator-driven | `src/review_gate.py`, `src/publish_reviewed.py`; real CLI/publish walkthrough still required |

## Remaining 1.0 engineering validation

- [ ] Pull latest `task/1-foundation-schema` and run `ruff check src tests`.
- [ ] Run `pytest tests/ -v`, paying particular attention to `test_force_failure_archives_old_card_and_excludes_it_from_dashboard`.
- [ ] Run `python src/import_questions.py` and `python src/generate_vault.py --config config.toml --dry-run`; verify current fixture count and canonical validation.
- [ ] Run a small candidate generation with a known-good model response; verify card, assets, and daily dashboard.
- [ ] Run the same command again without `--force`; verify no LLM calls occur for existing cards.
- [ ] Force a regeneration failure; verify the old card is moved under `.stale_candidates/` and not linked from the active dashboard.
- [ ] Exercise `src/review_gate.py` with known passing and failing review evidence; exercise `src/publish_reviewed.py` to prove ACCEPT can publish and REVIEW/REJECT cannot.
- [ ] Open the candidate Vault in Obsidian and manually check callouts, LaTeX, relative image paths and internal links.
- [ ] Mark the pipeline 1.0 engineering milestone complete only after the above checks pass. This does not mark generated educational content as approved.

## Next phase — model comparison, not more Prompt churn

- [ ] Freeze the current shared Prompt during the comparison experiment.
- [ ] Select a fixed, representative set of questions including the three pilot cases.
- [ ] Generate candidate outputs from local Qwen and cloud Gemini / ChatGPT / DeepSeek where available; record model/version, config, latency, parse/integrity outcome and review rubric results.
- [ ] Compare correctness, reasoning completeness, formula/unit integrity, LaTeX integrity, student clarity, and runtime/cost. Do not overwrite one model's result with another's.
- [ ] Send failed cards to per-card correction/manual review; revise the shared Prompt only if the same material defect recurs across distinct questions or a critical systemic defect is found.

## Deferred product scope

- [ ] Curate at least 20 real questions with confirmed knowledge points, question type and difficulty; remove import placeholders.
- [ ] Evaluate OCR-assisted capture cost and diagram/image workflow.
- [ ] Measure whether daily dashboard and Funny memory aids improve study start-up or recall.
- [ ] Consider content-hash invalidation for changes to canonical questions and automatic model-review orchestration only after the basic workflow is stable.
