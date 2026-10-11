# Funny Tutor — Technical Debt Register

Last reviewed: 2026-10-11  
Scope: evidence-based debt found while tracing `idea.md` → `spec.md` → `tasks/plan.md` / `tasks/todo.md` → implementation and the three-question pilot.

## Executive summary

The engineering path is largely implemented: canonical schema/import, configurable LiteLLM client, strict Generate payload, Markdown renderer, daily dashboard, incremental/force pipeline, deterministic text-integrity gate, and a manual review/publish boundary exist. The user reports `ruff check src tests` and `pytest tests/ -v` pass on the local branch before the newest stale-card regression change.

The three-question Qwen pilot is **not content-approved**. Two generated cards still have material physics-content defects, and the capacitor card's latest forced generation was rejected because JSON decoding produced control characters. This is tracked as content/runtime debt, not a reason to endlessly extend the shared Prompt.

## P0 — Resolve before promoting generated cards

### TD-001 — Model-generated physics content can violate explicit constraints

- **Evidence:** The rain-drop card said a charge magnitude larger than the threshold could still maintain static suspension. Under the stated two-force model, equilibrium requires `|q|E = mg`; a smaller electric force cannot balance gravity and a larger one gives a nonzero upward resultant.
- **Evidence:** The charged-particle card used `R=mv/(qB)` without defining `q` as charge magnitude; the positive radius formula should use `|q|`.
- **Impact:** Incorrect teaching material can look fluent and complete despite a successful generation status.
- **Mitigation for 1.0:** Treat all model output as candidate content. Use a fixed review rubric and card-level human/model review; do not promote unresolved critical defects. Do not keep expanding the shared Prompt as the default response.
- **Owner / next action:** Pipeline owner; include the three pilot questions in the fixed Qwen/cloud comparison set and preserve per-model outputs.

### TD-002 — JSON can parse while LaTeX commands are corrupted

- **Evidence:** The capacitor generation was rejected because decoded `funny_explanation` contained forbidden control characters `U+000C` (form feed) and `U+0009` (tab). JSON escapes such as `\\f` or `\\t` can transform an intended LaTeX command into a control character if the model emits invalidly escaped JSON.
- **Impact:** Formula text may silently break if this boundary is bypassed.
- **Current protection:** `src/quality_gate.py` rejects decoded control characters before rendering. Keep this rejection; do not weaken the gate.
- **Mitigation:** Add bounded, targeted retry/repair only if the product needs it; otherwise fail the card visibly and continue the batch. Any retry must pass the same parser, schema and integrity checks. Inspect final Markdown for intact formulas.
- **Status:** Gate implemented; targeted repair/retry not implemented.

### TD-003 — Failed forced generation can leave an old card at the active path

- **Evidence:** The generator writes a card only after validation and rendering, so a failed `--force` run can leave the previous card at its normal path. The pilot then still showed a capacitor Markdown file even though the current run failed for that question.
- **Impact:** A stale candidate can be mistaken for fresh output.
- **Change made:** `src/generate_vault.py` now archives an existing card under `.stale_candidates/` if forced regeneration fails and builds the dashboard only from successfully generated or intentionally skipped cards. A regression test was added to `tests/test_generate_vault.py`.
- **Status:** Code and test committed; **local Ruff/pytest must be rerun after pulling this change**. This change reduces stale-card confusion but does not make a generated card semantically correct.

## P1 — 1.0 workflow completeness / usability

### TD-004 — Review aggregation is not model orchestration

- **Current implementation:** `src/review_gate.py` aggregates saved structured review reports; `src/publish_reviewed.py` checks an ACCEPT decision before promotion.
- **Gap:** The CLI does not call the independent solver or reviewer models, prove that the solver saw no canonical answer, or establish that reviewer IDs represent genuinely independent systems.
- **Mitigation:** For 1.0, execute solver-first/reviewer-second manually and save reports. Run known passing/failing fixtures through both CLIs. Model agreement is evidence, not proof.
- **Deferred:** Provider orchestration, immutable provenance, and a human-review UI.

### TD-005 — End-to-end validation is incomplete despite unit-test success

- **Evidence:** The user reports current `ruff` and `pytest` are passing, but the latest three-question real-model pilot had `generated=2, failed=1`; the failed capacitor generation was blocked by the integrity gate. The remaining two outputs were not both semantically acceptable.
- **Impact:** Unit tests do not exercise the full range of model outputs or guarantee Obsidian rendering.
- **Next actions:** Pull the latest generator/test changes; rerun lint/tests; perform a small known-good end-to-end run, incremental rerun, forced-failure test, review CLI/publisher walkthrough, and manual Obsidian check.

### TD-006 — The source-of-truth / LLM calculation boundary is inconsistent

- **Original idea/spec:** The LLM is a language-and-memory amplifier, not the authoritative solver; quantitative conclusions should follow the official analysis.
- **Recent pilot constraints:** The Funny explanation is also asked to reproduce explicit numerical chains and independently use rigorous equivalent formulas.
- **Impact:** The boundary between preserving official solution content and allowing the model to independently recalculate is ambiguous. It may cause both blind copying of OCR-corrupted formulas and unsupported model derivations.
- **Decision needed:** For the first comparison release, preserve canonical question/answer/official analysis unchanged, allow a candidate explanation to restate formulas only with explicit review, and mark any independent recalculation as a claim requiring verification. Do not treat generated calculations as canonical truth.

### TD-007 — Canonical import uses placeholders, not curated educational metadata

- **Evidence:** The current fixture imports 10 records. Knowledge paths/points, question type and difficulty are marked with placeholder values such as `待标注` or default difficulty 3.
- **Impact:** Schema validity can be mistaken for pedagogical readiness; knowledge-tree navigation is not yet curated.
- **Mitigation:** Keep placeholder tags visible and do not treat these records as a curated 20-question bank.
- **Deferred:** Human annotation and curation to at least 20 questions.

### TD-008 — Real Obsidian rendering and asset verification are not signed off

- **Implemented:** Renderer emits callouts, tags, knowledge links, and relative asset references; the pipeline copies assets into the Vault.
- **Gap:** Automated string tests do not prove that all formulas, callouts, links, and image paths display correctly in the actual Obsidian app.
- **Next action:** Open the candidate Vault and check at least one card with images and LaTeX. The current three-question pilot may not cover image rendering.

## P2 — Model comparison and evaluation

### TD-009 — No fixed cross-model benchmark/report yet

- **Goal:** Compare local `qwen3.5:9b-opencode` against cloud Gemini, ChatGPT and DeepSeek using the same source questions and frozen prompts.
- **Gap:** The project has no single persisted experiment matrix with model/version, parameters, latency, parse/integrity outcome, content rubric, and final review decision.
- **Next action:** Use a fixed representative set (at least the three pilot cases), save every model output separately, and compare against one rubric. Do not overwrite canonical data or one model's output with another's.

### TD-010 — Prompt-specific rules and semantic checks remain partly manual

- **Evidence:** The Qwen model violated rules that were already stated explicitly. Pydantic/JSON Schema checks shape and types, not physics meaning.
- **Decision:** Freeze shared Prompt during the first cross-model comparison. Add deterministic validators only for objective invariants that are stable and testable. Route nuanced reasoning/clarity defects to review rather than creating an ever-growing list of prompt instructions.
- **Stop rule:** Reopen the shared Prompt only for a critical systemic issue or the same material failure recurring across multiple distinct questions.

## P3 — Product hypotheses not yet validated

### TD-011 — Original 20-question and OCR workflow assumptions remain unvalidated

- **Original idea:** 20 questions, image/diagram references, OCR-assisted Inbox capture, theme and daily micro-learning.
- **Current state:** Current fixture has 10 imported records; OCR capture automation, a polished theme, and a measured learning-retention study are not implemented.
- **Decision:** These are deferred beyond pipeline-first 1.0, not silently counted as completed.

## 1.0 exit checklist

- [ ] Latest `ruff check src tests` passes after the stale-card safeguard change.
- [ ] Latest `pytest tests/ -v` passes, including forced-generation failure archival.
- [ ] Small end-to-end generation succeeds with a known-good response; dashboard links only to active cards.
- [ ] Second non-force run skips existing cards without LLM calls.
- [ ] Force failure archives stale content and does not present it as fresh.
- [ ] Review CLI and publish CLI are exercised with pass and fail evidence.
- [ ] Candidate Vault is opened in Obsidian; LaTeX, callouts, links, and image paths are manually checked.
- [ ] Fixed cross-model experiment set and rubric are prepared; no further open-ended shared-Prompt tuning.

**Release language:** Passing this checklist closes the pipeline-focused engineering milestone. It does not certify every model-generated explanation or turn placeholder records into curated educational content.
