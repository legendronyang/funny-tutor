# Funny Tutor — Quality Gate v1 Runbook

## Purpose

Generated teaching content is a candidate, not a trusted answer. The quality gate defines evidence thresholds for release; it cannot guarantee absolute correctness. Keep source question, canonical answer, and official analysis immutable.

## 1. Local checks

From the repository root:

```bash
ruff check src tests
pytest tests/ -v
```

Do not use real-model calls as a substitute for unit tests. The new tests cover control characters, review aggregation, and publication blocking; run them locally before reviewing any new pilot output.

## 2. Stage the candidate

Use a separate candidate Vault, such as `vault/FunnyTutor_EM_Pilot`. Do not treat a generated Markdown file as approved merely because the pipeline reports `generated=1`.

## 3. Independent first-pass solve

For each question and each reviewer model, first send the question statement and options only, using `src/prompts/independent_solver.txt`. Do not expose the canonical answer, official analysis, or candidate explanation in this first call. Save the raw response and parsed result before continuing.

## 4. Review the candidate

Only after saving the first-pass solution, send the reviewer the candidate card, canonical answer/official analysis, and the saved independent solution. Use `src/prompts/review_gate.txt` and require a JSON object matching `ReviewReportPayload`. Save the original reviewer response as well as the parsed JSON. Use two distinct reviewer model identifiers; model-name diversity is a practical heuristic, not proof of independence.

## 5. Aggregate saved evidence

Create an input JSON file with this shape:

```json
{
  "question_id": "em-example",
  "canonical_answer": ["B"],
  "reviews": [
    {
      "reviewer_model": "provider/model-a",
      "independent_answer": ["B"],
      "review": {
        "answer_correctness": {
          "status": "PASS",
          "evidence": ["Independent derivation leads to option B."],
          "issues": []
        },
        "physics_reasoning": {
          "status": "PASS",
          "evidence": ["The stated equilibrium condition supports the relation."],
          "issues": []
        },
        "formula_units": {
          "status": "PASS",
          "evidence": ["Variables and SI units are consistent."],
          "issues": []
        },
        "numerical_consistency": {
          "status": "PASS",
          "evidence": ["The arithmetic and order of magnitude agree."],
          "issues": []
        },
        "student_clarity": {
          "status": "PASS",
          "evidence": ["The explanation connects conditions to the result."],
          "issues": []
        },
        "latex_integrity": {
          "status": "PASS",
          "evidence": ["All formulas are intact in the rendered candidate."],
          "issues": []
        },
        "issues": []
      }
    },
    {
      "reviewer_model": "provider/model-b",
      "independent_answer": ["B"],
      "review": {
        "answer_correctness": {
          "status": "PASS",
          "evidence": ["A separately derived solution agrees with B."],
          "issues": []
        },
        "physics_reasoning": {
          "status": "PASS",
          "evidence": ["The physical assumptions are stated."],
          "issues": []
        },
        "formula_units": {
          "status": "PASS",
          "evidence": ["The formula dimensions are consistent."],
          "issues": []
        },
        "numerical_consistency": {
          "status": "PASS",
          "evidence": ["The result matches the calculation."],
          "issues": []
        },
        "student_clarity": {
          "status": "PASS",
          "evidence": ["The explanation is understandable and complete."],
          "issues": []
        },
        "latex_integrity": {
          "status": "PASS",
          "evidence": ["The rendered formulas are intact."],
          "issues": []
        },
        "issues": []
      }
    }
  ]
}
```

This is a schema example only, not real review evidence. Do not copy the sample evidence and claim a real review was performed.

Run:

```bash
python src/review_gate.py \
  --input /tmp/em-example-reviews.json \
  --output /tmp/em-example-decision.json
```

The CLI prints the computed decision and saves reports plus reasons. It does not call LLMs or verify that the reviewer actually followed the staged protocol.

## 5.1 Pilot regression checklist

The first three-question pilot exposed semantic issues that syntax/schema checks cannot catch. Recheck these after regenerating candidates:

- **Rain-drop equilibrium:** explicitly show `r=1 mm=10^-3 m` and `r^3=(10^-3 m)^3=10^-9 m^3`; include the full numerical chain for volume, mass, weight, and `|q|`; explain why a charge magnitude below `mg/E` cannot balance gravity. Keep the millimetre-to-metre error (`10^9` impact) distinct from a cubic-power error (`10^6` impact).
- **Charged particle in a magnetic field:** for a positive orbit radius, use `|q|vB=mv^2/R` and `R=mv/(|q|B)`, unless the notation explicitly defines `q` as charge magnitude. Check the same convention in angular velocity formulas. Do not copy a questionable OCR formula from the read-only official analysis into new teaching content.
- **Capacitor with dielectric removed at constant voltage:** use the stated constraints directly: `E=U/d` stays constant when `U` and `d` stay constant; `C` decreases and `Q=CU` decreases. If discussing an alternative field expression involving charge and permittivity, track all changing variables together; do not call a formula invalid merely because one of its variables changes.

These are candidate-review criteria, not automatic proof of correctness. A regenerated card remains a candidate until independent review evidence supports promotion.

## 6. Publication

Only use the promotion script after generating real review evidence:

```bash
python src/publish_reviewed.py \
  --candidate-card vault/FunnyTutor_EM_Pilot/path/em-example.md \
  --decision-file /tmp/em-example-decision.json \
  --question-id em-example \
  --destination vault/FunnyTutor_EM_Vault/path/em-example.md
```

The publisher requires a matching question ID, ACCEPT decision, at least two distinct reviewer identifiers, MATCH status, and PASS on every required dimension. REVIEW or REJECT must never be promoted. Keep the original candidate and review evidence for audit.

## Decision meanings

- **ACCEPT:** The defined evidence threshold was met. This is not proof of absolute correctness.
- **REVIEW:** Evidence is insufficient, ambiguous, conflicting, or uncertain; human review is needed.
- **REJECT:** A required review dimension has an explicit, evidence-backed failure.

## Known limitations

- Model orchestration is not automated yet. The operator must enforce independent-first solving before showing the answer/official analysis.
- Reviewer IDs are strings supplied by the operator; they do not cryptographically establish provider or model independence.
- This gate checks output integrity and review evidence, not the full semantic correctness of arbitrary physics.
- The generated content remains a candidate until the explicit promotion step succeeds.
