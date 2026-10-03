# Funny Tutor — AI Domain Knowledge & Personalized Learning OS Research

> Research date: 2026-10-03  
> Target repository: `legendronyang/funny-tutor`  
> Document purpose: Preserve the current session's conclusions as a durable research and architecture reference.

## 1. Core idea discussed in this session

The target product is broader than a normal AI Tutor. It aims to build a systematic, evidence-grounded view of an entire domain and connect that domain model to a learner's real learning evidence.

The intended closed loop is:

```text
Domain Area
   ↓
Canonical Knowledge Graph / Knowledge Tree
   ↓
Exam / Notes / Textbook / Questions
   ↓
Knowledge-point Mapping
   ↓
Student Knowledge State
   ↓
Wrong-answer / Misconception Diagnosis
   ↓
Multimodal Resource Retrieval
   ↓
AI Micro-Lesson / Video
   ↓
Targeted Practice / Past Questions
   ↓
Re-assessment
   ↺
```

Example domains include High-school Physics, AI Agents, Computer Networks, and specialized engineering domains such as Broadcom Tomahawk 6 / FBOSS.

A useful product description is:

> **AI-powered Domain Knowledge Graph + Personal Learning Graph + Multimodal Tutor**

A concise product concept is:

> **AI Knowledge Learning OS**

---

## 2. Capability A — Domain → complete knowledge view

A user enters a domain such as `高中物理`, `AI Agent`, or `Data Center Ethernet Switching`.

The desired output is not a shallow LLM outline, but an expandable domain knowledge structure:

```text
Root Domain
 ├─ Area / Chapter
 │   ├─ Concept
 │   ├─ Skill
 │   ├─ Formula / Rule
 │   ├─ Experiment / Procedure
 │   ├─ Typical Problem
 │   └─ Prerequisites
 └─ ...
```

A better technical definition than “generate all knowledge points” is:

> **Build a canonical, evidence-grounded, expandable knowledge space for a domain.**

The knowledge model should contain authoritative-source evidence and provenance, and should support versioning and later expansion.

### Knowledge is more than a tree

A strong domain model should represent at least four dimensions:

1. **Declarative knowledge** — definitions, facts, terminology, formulas, laws.
2. **Procedural knowledge / skills** — solving, deriving, debugging, configuring, operating.
3. **Thinking / reasoning patterns** — decomposition, causal reasoning, abstraction, proof, estimation, diagnosis.
4. **Relationships** — prerequisite, parent/child, related concept, misconception, tested-by, demonstrated-by, supported-by.

This is why the long-term data model should be a **knowledge graph / knowledge space**, not merely an outline.

---

## 3. Capability B — Exam / notes → knowledge-point coverage

Inputs may include:

- Exam papers
- Homework
- Wrong-answer notebooks
- Personal notes
- Textbook PDFs
- Scanned images

The system extracts questions or semantic units and maps them into the domain graph.

Example:

```text
Question #17
   ↓
Concept: Newton's Second Law
   ↓
Skill: Free-body diagram
   ↓
Prerequisites:
    vector decomposition
    acceleration
    force balance
   ↓
Difficulty / competency requirements
```

The useful output is not merely “Question 17 is about Newton's Second Law”. It should expose:

```text
Question
 ├─ concept(s)
 ├─ skill(s)
 ├─ prerequisite(s)
 ├─ reasoning pattern
 ├─ formula / rule dependencies
 ├─ difficulty
 └─ evidence / confidence
```

This creates the bridge between a static domain map and an actionable learner model.

---

## 4. Capability C — Wrong answer → diagnosis → multimodal teaching → practice

For each wrong answer:

```text
Wrong Question
   ↓
Knowledge Point Mapping
   ↓
Root-cause / misconception diagnosis
   ↓
Retrieve relevant resources
   ├─ Text
   ├─ Images / diagrams
   ├─ Videos
   ├─ Slides
   └─ Examples
   ↓
Teaching Plan
   ↓
AI-generated concise explanation
   ↓
Micro-lesson / video
   ↓
Related past questions
   ↓
Re-test
   ↓
Update student mastery state
```

The system should distinguish at least:

- Missing knowledge
- Missing prerequisite
- Procedural / skill error
- Misconception
- Calculation / execution error
- Reading / interpretation error
- Careless mistake

This is much more useful than simply assigning one knowledge-point label.

---

# 5. Open-source landscape discovered

## 5.1 LearningMAP

Repository: https://github.com/ai-for-edu/LearningMAP

Positioning: a personalized learning tutor.

Key ideas:

- Topic → knowledge graph
- Adaptive quiz
- Grading
- Diagnosis
- Targeted lesson
- Slide deck
- Learner memory

Conceptually:

```text
Topic
 ↓
Knowledge Graph
 ↓
Assessment
 ↓
Diagnosis
 ↓
Targeted Learning
```

Why it matters: it is one of the closest open-source references for the overall personalized learning loop.

Relative gaps to the Funny Tutor vision include user-uploaded exam/notes as a core ingestion path, broad web-scale multimodal retrieval, and a complete automatic video-generation loop.

---

## 5.2 K12-KGraph

Repository: https://github.com/haolpku/K12-KGraph

Positioning: curriculum-aligned knowledge graph, benchmark and multimodal educational dataset for educational LLMs.

Representative ontology:

```text
Book
 ↓
Chapter
 ↓
Section
 ↓
Concept
 ↓
Skill
 ↓
Experiment
 ↓
Exercise
```

Representative relations:

```text
is_a
prerequisites_for
relates_to
verifies
tests_concept
tests_skill
appears_in
leads_to
is_part_of
```

This project is especially relevant to Chinese K-12 / High-school Physics because it models concepts, skills, prerequisites, experiments and exercises as a structured graph.

Key lesson:

> A useful knowledge tree should evolve into a knowledge graph with semantic relationships, prerequisites, evidence and exercises.

---

## 5.3 Knowledge Spaces

Repository: https://github.com/vanderbilt-data-science/knowledge-spaces

Positioning: AI-powered Knowledge Space Theory for adaptive education.

Conceptual pipeline:

```text
Course materials
 ↓
Atomic knowledge items
 ↓
Prerequisite relationships
 ↓
Knowledge space
 ↓
Adaptive assessment
 ↓
Personalized materials
 ↓
JIT instruction planning
```

Particularly relevant: the project uses Claude Code skills to implement a Knowledge Space workflow. This makes it a useful reference for combining **Agent Skills + knowledge modeling + adaptive education**.

---

## 5.4 education_knowledge_graph_app

Repository: https://github.com/jiangnanboy/education_knowledge_graph_app

The project models:

- K-12 educational knowledge graph
- Graph visualization
- Knowledge-point tracking
- Intelligent Q&A
- Question → knowledge-point prediction
- Parent/child knowledge traversal
- Knowledge-path queries

It is a useful traditional architecture reference for:

```text
Subject
 ↓
Knowledge Graph
 ↓
Question
 ↓
Knowledge Points
 ↓
Relationship / Path
```

It is not the recommended modern foundation for the whole Funny Tutor stack, but it is valuable for understanding question-to-knowledge mapping.

---

# 6. Student knowledge state / knowledge tracing

## 6.1 pyBKT

Repository: https://github.com/CAHLR/pyBKT

Bayesian Knowledge Tracing provides a useful mental model:

```text
Question
 ↓
Skill
 ↓
Correct / Wrong sequence
 ↓
Mastery probability
```

The important transition is from:

> “Which knowledge point does this question test?”

to:

> “What is the student's current estimated mastery of this skill?”

---

## 6.2 pyKT

Repository: https://github.com/pykt-team/pykt-toolkit

A Knowledge Tracing research toolkit that can be used as a reference for modeling and evaluating student mastery over time.

---

# 7. Multimodal resource retrieval

## Multimodal-Video-RAG

Repository: https://github.com/iisc-kc/Multimodal-Video-RAG

Positioning: agentic multimodal video RAG for lecture understanding with open-source models.

Conceptual pipeline:

```text
Video
 ├─ Audio / transcript
 ├─ Frames
 ├─ Slides
 ├─ OCR
 └─ visual semantics
        ↓
Multimodal RAG
        ↓
Retrieval / reasoning
```

This is useful for the resource layer:

```text
Knowledge Point
 ↓
Resource Search
 ├─ text
 ├─ image
 ├─ video
 ├─ slide
 └─ lecture
```

### Resource provenance should be first-class data

A resource record should ideally preserve:

```text
source
URL
author
timestamp
license
knowledge_points
difficulty
credibility
retrieval_score
```

Generated teaching content should be traceable to source material whenever possible.

---

# 8. AI-generated educational video

## 8.1 AnimEd-AI

Repository: https://github.com/mustansirr/AnimEd-AI

Positioning: agentic AI for curriculum-aligned educational video generation using LLMs, RAG and Manim.

Representative pipeline:

```text
Prompt / source material
 ↓
Planner Agent
 ↓
Script Agent
 ↓
Reviewer Agent
 ↓
Code generation
 ↓
Manim
 ↓
Video
```

This is highly relevant to the future micro-lesson generation layer.

---

## 8.2 manim-shorts

Repository: https://github.com/sohxmg/manim-shorts

Useful concepts include:

- Multi-agent orchestration
- Dual RAG
- Self-healing code generation
- Short educational video generation
- TTS

Representative pipeline:

```text
Topic
 ↓
Script generation
 ↓
Animation plan
 ↓
RAG
 ↓
Manim code
 ↓
Review / self-healing
 ↓
TTS
 ↓
Video
```

The self-healing concept is valuable because generated animation code can fail and needs iterative validation.

---

## 8.3 Generative Manim

Repository: https://github.com/marcelo-earth/generative-manim

Core idea:

```text
Natural language
 ↓
LLM
 ↓
Manim program
 ↓
Video
```

Useful as a lower-level reference for text-to-visual explanation.

---

## 8.4 Manim Community

Repository: https://github.com/ManimCommunity/manim

A mature open-source scientific/math animation engine and a useful execution layer for generated visual explanations.

---

# 9. Past exam / benchmark data

## GAOKAO-Bench

Repository: https://github.com/OpenLMLab/GAOKAO-Bench

Useful as a source/reference for Chinese Gaokao question-oriented workflows.

Important distinction:

> A benchmark dataset is not the same thing as a personalized recommendation engine.

Funny Tutor should eventually perform:

```text
Wrong question
 ↓
Knowledge point
 ↓
Related prerequisite / neighbor skills
 ↓
Past questions
 ↓
Difficulty progression
 ↓
Re-test
```

rather than only retrieving superficially similar questions.

---

# 10. Comparative landscape

| Project | Knowledge Graph | Question → Knowledge | Student State | Multimodal RAG | Personalized Learning | Video Generation |
|---|---:|---:|---:|---:|---:|---:|
| LearningMAP | ✅ | ✅ | ✅ | Partial | ✅ | ❌ |
| K12-KGraph | ✅✅ | ✅✅ | Partial | ✅ | Partial | ❌ |
| Knowledge Spaces | ✅✅ | ✅ | ✅✅ | Partial | ✅ | ❌ |
| education_knowledge_graph_app | ✅ | ✅✅ | Partial | ❌ | Partial | ❌ |
| pyBKT | Partial | ✅ | ✅✅ | ❌ | ❌ | ❌ |
| pyKT | Partial | ✅ | ✅✅ | ❌ | ❌ | ❌ |
| AnimEd-AI | Partial | Partial | ❌ | ✅ | ✅ | ✅✅ |
| manim-shorts | ❌ | ❌ | ❌ | ✅ | ❌ | ✅✅ |
| Generative Manim | ❌ | ❌ | ❌ | Partial | ❌ | ✅ |
| Multimodal-Video-RAG | Partial | Partial | Partial | ✅✅ | Partial | ❌ |
| GAOKAO-Bench | ❌ | Partial | ❌ | ✅ | ❌ | ❌ |

The key finding is **composability**. The ecosystem contains good parts for nearly every layer, but not one mature project that fully closes the loop.

---

# 11. Proposed Funny Tutor architecture

```text
┌───────────────────────────────────────────────────────┐
│                    User / Learner                     │
│  Domain | Exam | Notes | Wrong Question | Goal         │
└─────────────────────────┬─────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────┐
│              Domain Knowledge Engine                   │
│  Ontology | Taxonomy | Concepts | Skills | Prereqs    │
│  Evidence | Versioning | Curriculum Alignment         │
└─────────────────────────┬─────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────┐
│               Content / Question Mapping               │
│  PDF/Image/OCR | Question Extraction | KG Mapping      │
│  Concept/Skill/Prerequisite/Difficulty                 │
└─────────────────────────┬─────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────┐
│                Personal Learning Graph                 │
│  Mastery | Attempts | Errors | Misconceptions | Goals   │
└─────────────────────────┬─────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────┐
│                Diagnosis & Planning Agents             │
│  Root Cause | Next Knowledge Node | Learning Strategy  │
└─────────────────────────┬─────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────┐
│                Multimodal Resource Layer               │
│  Web | PDF | Image | Video | Slides | Examples         │
│  Retrieval | Ranking | Provenance | Verification       │
└─────────────────────────┬─────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────┐
│                 Teaching Generation                    │
│  Explanation | Diagram | Animation | Slides | TTS      │
│  Micro-lesson | Video                                  │
└─────────────────────────┬─────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────┐
│                  Practice / Assessment                 │
│  Related Questions | Past Exams | Difficulty Ladder   │
└─────────────────────────┬─────────────────────────────┘
                          ↓
                    Student Update
                          ↺
```

---

# 12. Recommended data model

## 12.1 Knowledge node

```yaml
id:
domain:
title:
type: concept | skill | formula | experiment | reasoning_pattern
parent_ids:
prerequisite_ids:
related_ids:
definitions:
core_knowledge:
procedures:
reasoning_patterns:
common_misconceptions:
example_questions:
difficulty:
curriculum_refs:
evidence:
resources:
version:
confidence:
```

## 12.2 Question-to-knowledge mapping

```yaml
question_id:
domain:
concept_ids:
skill_ids:
prerequisite_ids:
reasoning_pattern_ids:
difficulty:
question_type:
solution_outline:
common_error_types:
evidence:
confidence:
```

## 12.3 Student learning state

```yaml
student_id:
knowledge_node_id:
mastery_probability:
evidence_count:
recent_attempts:
error_patterns:
last_assessed_at:
recommended_next_action:
```

---

# 13. Evidence-grounded web resource retrieval

Do not define the product feature simply as “search the internet and return links”. Use an evidence-grounded pipeline:

```text
Knowledge Point
 ↓
Candidate resources
 ↓
Semantic + multimodal retrieval
 ↓
Source credibility
 ↓
Curriculum alignment
 ↓
Difficulty alignment
 ↓
License / usage check
 ↓
Evidence extraction
 ↓
Ranked resources
```

Generated lessons should retain provenance to important source claims, ideally down to document section/page or video timestamp where practical.

---

# 14. Agent / Skill decomposition

A future Skills-based implementation could contain:

```text
/domain-discover
/domain-ontology
/knowledge-extract
/knowledge-validate
/knowledge-link
/question-extract
/question-map
/diagnose-mistake
/estimate-mastery
/resource-search
/resource-rank
/lesson-plan
/explanation-generate
/video-generate
/practice-recommend
/mastery-update
```

This aligns naturally with the SDD direction discussed in the broader project context.

---

# 15. Relationship to SDD

Funny Tutor is a strong candidate for Specification-Driven Development because the difficult part is not only implementation; it is defining the domain model, contracts and system invariants.

Potential specification artifacts:

```text
spec/
 ├─ constitution.md
 ├─ domain-model.md
 ├─ knowledge-schema.md
 ├─ resource-provenance.md
 ├─ question-mapping.md
 ├─ student-model.md
 ├─ agent-contracts.md
 ├─ evaluation.md
 └─ roadmap.md
```

Early specifications should define:

- What qualifies as a knowledge node?
- What is the difference between concept, skill and reasoning pattern?
- How are prerequisites represented?
- How is evidence attached?
- How confident can an LLM be when creating, merging or deleting nodes?
- How do we detect that a domain map is incomplete?
- How does a question map to multiple concepts/skills?
- How are conflicting sources reconciled?

These definitions are more important than choosing a particular UI framework.

---

# 16. Practical MVP sequence

### MVP-1 — Domain Knowledge Map

Input: a bounded domain such as “高中物理”.

Output:

- Hierarchical knowledge tree
- Concepts
- Skills
- Prerequisite links
- Evidence

### MVP-2 — Question Mapping

Input: one exam PDF/image.

Output:

- Extracted questions
- Knowledge-point mapping
- Coverage matrix
- Uncovered / weakly evidenced nodes

### MVP-3 — Personal Learning Graph

Add:

- Correct/wrong history
- Mastery estimates
- Weak-node visualization
- Prerequisite-aware recommendations

### MVP-4 — Wrong-answer diagnosis

Input: wrong question.

Output:

- Tested knowledge
- Likely error type
- Prerequisite gaps
- Targeted learning plan

### MVP-5 — Multimodal resources

Retrieve text, images, videos and lecture clips with provenance.

### MVP-6 — AI micro-lesson

Generate:

- 1–5 minute explanation
- Diagram
- Slides
- Optional Manim animation
- TTS narration

### MVP-7 — Targeted practice loop

Recommend same-concept, prerequisite, related and historical questions with increasing difficulty, then update the student model.

---

# 17. Most important strategic conclusion

Do not try to reimplement every component.

A strong architecture can compose existing OSS/research components:

```text
K12-KGraph / Knowledge Spaces
          +
LearningMAP
          +
pyBKT / pyKT
          +
Multimodal-Video-RAG
          +
AnimEd-AI / Manim
          +
Exam datasets / retrieval
          +
LLM + Agents + Skills
```

The distinctive Funny Tutor value would be the **integration layer and unified model**:

```text
Canonical Domain Graph
         ↕
Question Graph
         ↕
Student Learning Graph
         ↕
Resource Graph
         ↕
Generated Teaching Artifacts
```

This is the architectural contribution that can turn the project from an AI chatbot into a learning system.

---

# 18. Open research questions

1. How can “domain completeness” be measured?
2. How can LLM-generated knowledge graphs be grounded and validated?
3. How should concepts, skills, reasoning patterns and misconceptions be separated?
4. How should prerequisite relationships be inferred and verified?
5. How should one question map to multiple knowledge nodes?
6. How should student mastery be estimated from sparse evidence?
7. How can misconception diagnosis be distinguished from simple concept classification?
8. How should web resources be ranked for correctness and pedagogical usefulness?
9. How can generated lessons retain traceability to trusted sources?
10. How can generated educational videos be automatically evaluated?
11. How should the system support multiple curricula, languages and educational systems?
12. How should copyright and licensing constrain retrieval and derived content?
13. How can the system detect that a domain graph has become stale?
14. How can two competing domain maps be compared and reconciled?

---

# 19. Working product thesis

> **Funny Tutor builds a living knowledge graph for a domain, maps real learning artifacts into that graph, maintains a personalized learner state, diagnoses gaps and misconceptions, retrieves trustworthy multimodal resources, generates concise evidence-grounded micro-lessons, and closes the loop with targeted practice and re-assessment.**

This is materially broader than “AI chatbot for learning”. It is closer to:

> **A personal knowledge-space and adaptive learning operating system.**

---

# 20. References identified in this research session

- LearningMAP — https://github.com/ai-for-edu/LearningMAP
- K12-KGraph — https://github.com/haolpku/K12-KGraph
- Knowledge Spaces — https://github.com/vanderbilt-data-science/knowledge-spaces
- education_knowledge_graph_app — https://github.com/jiangnanboy/education_knowledge_graph_app
- pyBKT — https://github.com/CAHLR/pyBKT
- pyKT — https://github.com/pykt-team/pykt-toolkit
- AnimEd-AI — https://github.com/mustansirr/AnimEd-AI
- manim-shorts — https://github.com/sohxmg/manim-shorts
- Generative Manim — https://github.com/marcelo-earth/generative-manim
- Manim Community — https://github.com/ManimCommunity/manim
- Multimodal-Video-RAG — https://github.com/iisc-kc/Multimodal-Video-RAG
- GAOKAO-Bench — https://github.com/OpenLMLab/GAOKAO-Bench

---

# 21. Final assessment from this session

The open-source ecosystem already contains substantial building blocks for:

- domain knowledge graphs
- adaptive learning
- knowledge tracing
- multimodal retrieval
- AI-generated educational videos
- exam/question datasets

However, the session did **not** identify a single mature open-source project that fully implements:

```text
Domain
 → Knowledge Graph
 → Exam / Notes Mapping
 → Student Model
 → Misconception Diagnosis
 → Multimodal Resource Retrieval
 → AI Micro-Lesson
 → Targeted Practice
 → Re-assessment
```

Therefore, Funny Tutor can reasonably be positioned as an **integration-first open-source project**, with the unified domain/student/resource graph and the closed-loop learning process as its central architectural contribution.
