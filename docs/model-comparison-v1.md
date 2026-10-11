# Funny Tutor Model Comparison v1

Date: 2026-10-11  
Status: protocol frozen for the first cross-model run; no model is presumed to be correct.

## 1. Purpose and boundary

Compare **generation quality** for the Funny Tutor explanation, memory aids and misconceptions on the same three canonical questions. This is not a benchmark of blind physics solving: the current generation pipeline supplies the canonical answer and official analysis to the generator, as specified by `src/generate_vault.py::_question_prompt`.

Independent correctness checking is a separate stage. First, a solver must see only the question and options and save its answer/reasoning. Only then may a reviewer see the saved first-pass solution, candidate card and canonical answer/official analysis.

Do not overwrite canonical input, another model's output, or the current Qwen baseline. All model output is a candidate.

## 2. Frozen question set

| ID | Topic | Important review focus |
|---|---|---|
| `em-2010-1-231c7037ec` | Raindrop suspended in a vertical electric field | Magnitude vs sign, static-equilibrium threshold, radius/volume units and numerical chain |
| `em-2015-20-fba9b68081` | Charged particle enters a weaker magnetic field | Use `|q|` for positive radius, speed conservation, radius and angular-velocity trend |
| `em-2016-24-4390f8caaf` | Capacitor with dielectric removed at constant voltage | `E=U/d`, capacitance/charge trend, preserve intact LaTeX |

Input dataset: `~/.config/funny-tutor/questions_em_pilot.json` in the user's WSL environment. Verify it contains exactly these three IDs before every run.

## 3. Models to compare

Run only the providers for which the user has working API credentials. Check availability using environment-variable names only; never print key values.

| Label | LiteLLM model string | Credential variable | Notes |
|---|---|---|---|
| Local baseline | `ollama_chat/qwen3.5:9b-opencode` | none | Existing output is in `C:\\Users\\river\\FunnyTutor_EM_Candidates`; snapshot it before comparison |
| Gemini | `gemini/gemini-3.8-flash` | `GEMINI_API_KEY` | Gemini 3 generation must not send legacy `temperature`; client compatibility test was added for this |
| OpenAI API | `openai/gpt-6-luna` | `OPENAI_API_KEY` | Use API access, not a ChatGPT browser transcript, for the timed generation run |
| DeepSeek API | `deepseek/deepseek-v4-flash` | `DEEPSEEK_API_KEY` | Use the V4 Flash model ID; the old `deepseek-chat` and `deepseek-reasoner` aliases were announced for retirement on 2026-07-24 |

Model IDs reflect official provider information checked on 2026-10-11. Confirm account access and the installed LiteLLM version before spending tokens:
- Google Gemini 3.8 Flash: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash
- OpenAI model catalog: https://developers.openai.com/api/docs/models
- DeepSeek API updates: https://api-docs.deepseek.com/zh-cn/updates/
- LiteLLM provider routing: https://docs.litellm.ai/

## 4. Fair-run controls

- Freeze `src/prompts/funny_tutor_em.txt` for the first experiment. Do not edit it between providers.
- Record `git rev-parse HEAD` and `git rev-parse HEAD:src/prompts/funny_tutor_em.txt` before the run.
- Use the same three-question JSON and the same renderer/client code; use a separate output Vault for every provider.
- Set each model configuration's `questions_json` to the same Pilot JSON and `vault_dir` to a dedicated Windows-local folder such as `C:\\Users\\river\\FunnyTutor_ModelComparison\\gemini-3.8-flash`.
- Do not use `--force` during first run. A clean, provider-specific output directory should generate three cards. Capture total elapsed time from the command or per-call timestamps.
- The current client omits `temperature` for Gemini 3 because the provider's current API documents the legacy sampling parameters as unsupported/deprecated. Therefore this is a practical comparison of each provider's recommended generation path, not a perfectly parameter-identical lab experiment; record that exception.
- Save generated files separately. Don't copy cloud results over the Qwen baseline and don't promote any candidate as official.

## 5. Fixed evaluation rubric

Do not reduce the review to a single overall average. A critical physics defect blocks publication regardless of style score.

### Hard checks (PASS / FAIL / UNCERTAIN)

1. Answer and physics conclusion agree with a valid derivation, not just the source answer.
2. Equations have valid assumptions, correct symbols/signs, dimensions and units.
3. Any numerical chain has correct arithmetic and magnitude.
4. LaTeX survives JSON parsing and renders as intended; no decoded control characters or broken commands.
5. No contradiction, invented condition or unsupported direction claim is introduced.

Any evidence-backed critical error = **FAIL** for that dimension and the candidate is not publishable. Insufficient evidence = **UNCERTAIN**, never silently PASS.

### Quality descriptors (0–2, with a short note)

- Student clarity: 0 unclear/incomplete, 1 usable but one meaningful gap, 2 clear and complete.
- Memory aids: 0 misleading/irrelevant, 1 relevant but generic, 2 memorable and physically faithful.
- Misconceptions: 0 wrong or not question-specific, 1 partially useful, 2 correct and targeted.

Always record evidence and the exact offending phrase/formula. Different models' reviewers should first solve independently; do not show canonical answer/analysis during that first pass.

## 6. Required run record

For every model/question, record:
- configured model string and date;
- repository commit and Prompt blob hash;
- generation status (generated / schema rejected / integrity rejected / provider error);
- elapsed seconds, plus token/cost metrics if available;
- candidate Markdown file path;
- results for each hard check and evidence;
- student-clarity, memory-aid and misconception ratings with notes;
- reviewer identity/configuration, independent answer and unresolved issues;
- final review workflow decision: ACCEPT / REVIEW / REJECT.

Use `experiments/model-comparison-v1/results.csv` as the run matrix. Raw outputs remain in model-specific folders outside the formal Vault.

## 7. Execution sequence

1. Snapshot the current Qwen cards into a read-only baseline folder.
2. Check which provider key variables are configured without echoing secrets.
3. Pull and validate the newly added Gemini 3 temperature compatibility change with Ruff/Pytest before any cloud call.
4. Start with one cloud provider, run the same three-question set into its own folder, and inspect latency/output. Only then run the other providers for which credentials are available.
5. Compare all outputs with the fixed rubric. Correct individual cards when necessary; do not tune the shared Prompt after each single failure.
6. Test `review_gate.py` and `publish_reviewed.py` with clearly synthetic pass/fail fixtures before using real review evidence. Synthetic fixtures are plumbing tests, never evidence that an actual card is correct.

## 8. Explicit current status

- Qwen generation pipeline: all three cards were produced across the last two non-force runs; the last run generated the capacitor card after repairing six malformed LaTeX escapes and skipped the other two existing cards.
- Obsidian display: user confirms all three cards display correctly in the Windows-local Candidates Vault.
- Content review: not complete; previous Qwen outputs have known physics issues. Passing display, JSON integrity, Ruff or pytest does not make a card content-approved.
- Cloud comparison: not yet run.
