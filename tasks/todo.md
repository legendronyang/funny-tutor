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
| Task 5 — Pipeline, assets, incremental/force behavior | IMPLEMENTED | `src/generate_vault.py`; pipeline tests; new stale-card-on-force-failure regression test passes in the user's latest local suite |
| Task 6 — Legacy import to Canonical JSON | DONE for current fixture | `src/import_questions.py`; prior local conversion of 10 records; annotations are explicit placeholders, not curated metadata |
| Task 7 — Strict Generate payload | DONE structurally | Pydantic + Ollama JSON Schema + control-character gate; semantic content still requires review |
| Task 8 — Evidence-based review and controlled publish | IMPLEMENTED, operator-driven | `src/review_gate.py`, `src/publish_reviewed.py`; real CLI/publish walkthrough still required |

## Remaining 1.0 engineering validation

- [x] Pull latest `task/1-foundation-schema` and run `ruff check src tests` — user log confirms `All checks passed!`.
- [x] Run `pytest tests/ -v`, including `test_force_failure_archives_old_card_and_excludes_it_from_dashboard` — user log confirms 85 passed in 6.03s in the latest user-provided pre-Gemini-compatibility-change run.
- [ ] Pull the newest Gemini 3 compatibility change and rerun `ruff check src tests` and `pytest tests/ -v` before any cloud generation; the new Gemini 3 test is not covered by the prior 85-test run.
- [ ] Run `python src/import_questions.py` and `python src/generate_vault.py --config config.toml --dry-run`; verify current fixture count and canonical validation.
- [x] Run a small three-question candidate generation to the Windows-local Vault; latest real Qwen run reports `total=3, generated=1, skipped=2, failed=0`, including successful bounded LaTeX escape recovery. Visual Obsidian/content review remains.
- [x] Run the same command without `--force`; latest log confirms two existing cards were skipped without LLM calls.
- [ ] Force a regeneration failure; verify the old card is moved under `.stale_candidates/` and not linked from the active dashboard.
- [ ] Exercise `src/review_gate.py` with known passing and failing review evidence; exercise `src/publish_reviewed.py` to prove ACCEPT can publish and REVIEW/REJECT cannot.
- [x] Open `C:\Users\river\FunnyTutor_EM_Candidates` in Obsidian; user confirms all three cards display normally. Note: image rendering remains unverified if the three pilot cards contain no image references.
- [ ] Mark the pipeline 1.0 engineering milestone complete only after the above checks pass. This does not mark generated educational content as approved.

## Next phase — model comparison, not more Prompt churn

- [x] Freeze the current shared Prompt during the comparison experiment; protocol and result matrix committed.
- [x] Select and freeze the three-question set; protocol is in `docs/model-comparison-v1.md`.
- [ ] Snapshot the current Qwen outputs; generate cloud candidates for providers whose credentials are available. Record outcomes in `experiments/model-comparison-v1/results.csv`.
- [ ] Compare correctness, reasoning completeness, formula/unit integrity, LaTeX integrity, student clarity, and runtime/cost. Do not overwrite one model's result with another's.
- [ ] Send failed cards to per-card correction/manual review; revise the shared Prompt only if the same material defect recurs across distinct questions or a critical systemic defect is found.

## Deferred product scope

- [ ] Curate at least 20 real questions with confirmed knowledge points, question type and difficulty; remove import placeholders.
- [ ] Evaluate OCR-assisted capture cost and diagram/image workflow.
- [ ] Measure whether daily dashboard and Funny memory aids improve study start-up or recall.
- [ ] Consider content-hash invalidation for changes to canonical questions and automatic model-review orchestration only after the basic workflow is stable.
