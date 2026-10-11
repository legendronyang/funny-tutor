# Funny Tutor

Funny Tutor is a pipeline-first project that turns canonical electromagnetism question records into Obsidian-native study cards and a daily dashboard. Canonical JSON remains the source of truth; LLM-generated explanations are candidates, not trusted answers.

## 1.0 status

The core engineering path is implemented: canonical schema/import, configurable LiteLLM client, strict Generate payload validation, Markdown renderer, daily dashboard, incremental generation, candidate Vault separation, and a manual evidence-based review/publish boundary.

The user has confirmed local `ruff check src tests` and `pytest tests/ -v` passed before the latest stale-card failure-handling regression was added. That newest change still needs local validation. The three-question real-Qwen pilot is **not content-approved**: two cards need physics-content correction, and one generation was rejected by the text-integrity gate.

- Current actionable checklist: [tasks/todo.md](tasks/todo.md)
- Requirements and implementation traceability: [spec.md](spec.md)
- Detailed implementation history and decisions: [tasks/plan.md](tasks/plan.md)
- Known limitations, failures and 1.0 exit criteria: [tech-debt.md](tech-debt.md)

## Run locally

```bash
python -m pip install -r requirements.txt
python src/import_questions.py
python src/generate_vault.py --config config.toml --dry-run
ruff check src tests
pytest tests/ -v
python src/generate_vault.py --config config.toml
```

The default configuration writes to `vault/FunnyTutor_EM_Candidates`. Do not treat candidate cards as approved teaching content or generate directly into `vault/FunnyTutor_EM_Vault`. Promotion requires a matching ACCEPT decision artifact through `src/publish_reviewed.py`.

## Current evaluation direction

Freeze the shared Prompt for the first comparison experiment. Run the same representative questions through local Qwen and available cloud models (Gemini, ChatGPT, DeepSeek), save outputs separately, and compare them with a fixed rubric. Do not continue unbounded Prompt tuning to make one local-model output pass.
