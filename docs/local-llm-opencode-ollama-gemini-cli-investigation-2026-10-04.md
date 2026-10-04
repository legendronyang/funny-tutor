# Funny Tutor — Local LLM / OpenCode / Ollama Performance Investigation

> Investigation date: 2026-10-04  
> Repository: `legendronyang/funny-tutor`  
> Purpose: Preserve the current deployment architecture, benchmark results, fault tree, eliminated causes, remaining hypotheses, and the next experimental direction for a local-first / cloud-escalation AI workflow.

---

## 1. Executive summary

This document records the investigation of a very slow **OpenCode + Ollama + Qwen3.5-9B** local coding-agent setup running inside **WSL2 Ubuntu on Windows 11**.

The most important conclusion is:

> **The observed multi-minute OpenCode latency is not explained by a broken Ollama model, broken tool calling, or the Windows/WSL/Clash network path. The dominant symptom is a very long wait before OpenCode receives the first response headers / first model output.**

The current evidence points toward a combination of:

- CPU-only local inference on an Intel i5-11400;
- high Ollama runtime memory usage for Qwen3.5-9B;
- OpenCode agent prompt / system / tool context overhead and prefill/cache work;
- OpenCode request/header timeout and retry behavior;
- possible request contention when Ollama is serving more than one client.

A second, separate architectural direction is now being explored:

> **Gemini CLI + LiteLLM + local Qwen3.5-9B, using a local-first / cloud-escalation model-routing strategy.**

This second direction is **not the cause of the historical OpenCode slowdown**. LiteLLM was installed **after** the OpenCode slow tests had already been completed.

---

# 2. Current deployment architecture

## 2.1 Physical / OS stack

\
\```text
┌──────────────────────────────────────────────────────────────┐
│                    Windows 11 Host                            │
│                                                              │
│  CPU: Intel Core i5-11400, 6C / 12T                         │
│  RAM: 32 GB                                                   │
│  GPU: Intel UHD (no useful NVIDIA CUDA acceleration)         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                    WSL2 Ubuntu                         │   │
│  │                                                        │   │
│  │  Ubuntu 24.04.4 LTS (Noble)                           │   │
│  │  WSL kernel: 6.18.40.1-1                              │   │
│  │  systemd=true                                         │   │
│  │  Approx. WSL memory available to VM: ~16 GiB          │   │
│  │  Swap: ~4 GiB                                         │   │
│  │                                                        │   │
│  │  ┌───────────────┐       ┌────────────────────────┐   │   │
│  │  │   OpenCode    │──────►│        Ollama           │   │   │
│  │  │   1.18.34     │ HTTP  │        0.35.1           │   │   │
│  │  │   Agent        │ :11434│        CPU inference     │   │   │
│  │  └───────────────┘       │                        │   │   │
│  │                           │ Qwen3.5:9b-opencode     │   │   │
│  │                           │ Q4_K_M / ~9.7B params   │   │   │
│  │                           └────────────────────────┘   │   │
│  │                                                        │   │
│  │  Additional tooling                                    │   │
│  │  - oh-my-opencode-slim 2.2.20                         │   │
│  │  - OpenCode Gemini auth plugin                        │   │
│  │  - LSP enabled                                         │   │
│  │  - Node.js v24.21.0 / npm+npx 12.1.0                  │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                              │
│  Clash Verge is the host-side network/proxy environment.     │
└──────────────────────────────────────────────────────────────┘
\```

### Important runtime facts

- Ollama reports the model as **100% CPU**.
- The model occupies about **8.7 GB** in \`ollama ps\`.
- During heavy runs the \`llama-server\` RSS was about **10 GB**, and \`systemctl status ollama\` later reported service memory around **12.8 GB** with a peak around **13.9 GB**.
- Swap usage remained negligible (roughly 1–2 MB in the service observation), so there is **no evidence of severe swap thrashing**.
- The observed local generation speed is approximately **5.5 tokens/s**.

---

# 3. OpenCode configuration under investigation

The relevant global configuration is approximately:

\```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama",
      "options": {
        "baseURL": "http://localhost:11434/v1"
      },
      "models": {
        "qwen3.5:9b": {
          "limit": {
            "context": 32768,
            "output": 4096
          }
        },
        "qwen3.5:9b-opencode": {
          "name": "Qwen3.5 9B - OpenCode",
          "limit": {
            "context": 65536,
            "output": 8192
          }
        }
      }
    }
  },
  "model": "ollama/qwen3.5:9b-opencode",
  "agent": {
    "build": {
      "mode": "primary",
      "model": "ollama/qwen3.5:9b-opencode"
    },
    "plan": {
      "mode": "primary",
      "model": "ollama/qwen3.5:9b-opencode"
    }
  },
  "plugin": [
    "opencode-gemini-auth",
    "oh-my-opencode-slim"
  ],
  "lsp": true
}
\```

For the critical performance experiments, \`--pure\` was used. That excludes external OpenCode plugins from the run, which is important when interpreting the results.

---

# 4. Model characteristics

Current local model:

\```text
Model                 qwen3.5:9b-opencode
Base                  qwen3.5:9b
Parameters            ~9.7B
Quantization          Q4_K_M
Ollama runtime        CPU-only
Configured context    65,536 tokens in OpenCode
ollama ps              100% CPU
Model/runtime size     ~8.7 GB shown by ollama ps
Observed generation   ~5.5 tok/s
\```

The purpose of the \`-opencode\` variant is to make the model usable in an OpenCode-style coding-agent workflow. The runtime context is configured at 64K+ because OpenCode's agent/tool workflow can require a large context.

A crucial distinction:

> The OpenCode provider \`limit.context\` setting describes what OpenCode is willing to send/accept; it is not by itself proof of the exact runtime context actually allocated by Ollama for every request.

---

# 5. Benchmark summary

## 5.1 Direct Ollama API

### Test A — \`/api/chat\`

Very small request:

\```text
User: Say exactly: OLLAMA_SPEED_OK
\```

Observed:

| Metric | Result |
|---|---:|
| Wall time | **14.44 s** |
| Ollama total duration | **14.38 s** |
| Model load duration | **12.94 s** |
| Prompt tokens | 20 |
| Output tokens | 5 |
| Prompt evaluation | ~0.71 s |
| Generation evaluation | ~0.73 s |

This demonstrates that Ollama can complete a tiny request successfully and quickly relative to the multi-minute OpenCode runs.

### Test B — OpenAI-compatible \`/v1/chat/completions\`

A similar tiny request through Ollama's OpenAI-compatible endpoint:

| Metric | Result |
|---|---:|
| Wall time | **~14.1 s** |
| Result | Successful |

### Test C — Explicit \`NO_PROXY\`

The same local \`/v1\` request was repeated with:

\```bash
NO_PROXY="localhost,127.0.0.1,::1"
no_proxy="localhost,127.0.0.1,::1"
\```

Result:

| Metric | Result |
|---|---:|
| Wall time | **14.92 s** |
| Result | Successful |

This is strong evidence that the local API itself is not suffering from an ordinary HTTP proxy routing problem.

---

## 5.2 OpenCode Agent benchmarks

| Test | OpenCode options | Result | Wall time |
|---|---|---|---:|
| Build / simple output | \`--pure --agent build\` | Correct output | **13m39s** |
| Build / simple output | \`--pure --agent build --variant none\` | Correct output | **7m40s** |
| Build + file read | \`--pure --agent build\` + \`read\` tool | Successfully read and summarized Markdown | **29m39s** |
| Plan / debug | \`--pure --agent plan --variant none\` | Correct output | **5m37s** |
| Build / debug | \`--pure --agent build --variant none\` | Correct output after retries | **15m03s** |
| Plan / direct network | \`NO_PROXY\` + \`--pure --agent plan --variant none\` | Correct output | **6m42s** |

### Interpretation

The important result is not simply that OpenCode is “slow”.

The timing shows that **the dominant delay occurs before the useful model response is delivered**.

---

# 6. Detailed evidence for the header / first-response problem

A debug run of the Plan agent produced:

\```text
03:17:12.687  request starts
03:22:06.573  ProviderHeaderTimeoutError
              Provider response headers timed out after 300000ms

03:22:09.019  retry begins
...
03:22:44.959  run ends
\```

The timeout is essentially the configured **300-second response-header timeout**.

A second Build debug run showed a much clearer pattern:

\```text
Attempt 1  → 300s header timeout
Attempt 2  → 300s header timeout
Attempt 3  → 300s header timeout
Attempt 4  → successful response
\```

Total wall time was approximately:

\```text
15m03s
\```

This explains a large fraction of the apparently mysterious multi-minute latency.

---

# 7. Session-level timing analysis

One exported OpenCode Plan session contained approximately:

\```json
{
  "modelID": "qwen3.5:9b-opencode",
  "providerID": "ollama",
  "agent": "plan",
  "variant": "none",
  "tokens": {
    "total": 8916,
    "input": 2727,
    "output": 45,
    "reasoning": 0,
    "cache": {
      "write": 0,
      "read": 6144
    }
  }
}
\```

The assistant response parts showed:

- small reasoning segment: ~11 s;
- final text: ~1 s;
- approximately **84 s elapsed before the first model output of the successful retry**.

This matters because it means:

> Once the request actually reaches the model and starts returning tokens, generation is not the main source of the five-to-fifteen-minute wall time.

The accounting also shows a significant amount of cached agent/context content. It is **evidence of non-trivial agent-context overhead**, but it should not be interpreted as a direct measurement of the exact HTTP request body size.

---

# 8. OpenCode statistics

One-day OpenCode statistics showed approximately:

\```text
Sessions              12
Messages               37
Avg tokens/session    ~9.6K
Median                ~8.6K
Input                 ~31.7K
Output                 ~2.5K
Cache Read            ~80.5K
\```

Model usage included:

\```text
ollama/qwen3.5:9b-opencode
  messages: 10
  input: ~26.6K
  output: ~829
  cache read: ~77.4K

ollama/qwen3.5:9b
  messages: 8
  input: ~5.1K
  output: ~1.7K
  cache read: ~3.1K
\```

Again, these numbers suggest that the coding-agent workflow has a much larger prompt/context footprint than the tiny direct Ollama test.

---

# 9. Ollama runtime observations

The Ollama service:

\```text
ollama.service
Main PID: 236
llama-server child process
Memory: ~12.8 GB
Memory peak: ~13.9 GB
Swap: ~1.8 MB
CPU: ~3h29m CPU time over ~2h17m uptime
\```

A later Ollama log contained a real request with timing information similar to:

\```text
n_gen = ~238 ... ~325
generation throughput = ~5.5 tok/s

POST "/api/chat"
duration = ~1m
slot id = 0
client cancelled after ~2,384 tokens processed
\```

This proves several things:

1. Ollama is actively running CPU inference.
2. The model can sustain around **5.5 tok/s**.
3. A real request can remain active for about a minute.
4. A client can cancel a request while Ollama is processing it.

However, this log is an **Ollama \`/api/chat\` request**, whereas OpenCode uses the OpenAI-compatible \`/v1\` path. Therefore it should not automatically be attributed to the OpenCode benchmark.

It is nevertheless useful evidence for a new hypothesis:

> **Concurrent clients / request contention should be checked whenever multiple local AI applications are active.**

---

# 10. Fault tree

## 10.1 Top-level symptom

\```text
OpenCode local-agent request takes 5–30+ minutes
                    │
                    ├── A. Network / proxy problem
                    │      ├── WSL networking
                    │      ├── Clash
                    │      └── HTTP proxy
                    │
                    ├── B. Ollama / model failure
                    │      ├── model cannot load
                    │      ├── inference hangs
                    │      └── tool calling broken
                    │
                    ├── C. CPU / memory pressure
                    │      ├── CPU-only inference
                    │      ├── high resident memory
                    │      └── swap thrashing
                    │
                    ├── D. OpenCode request path
                    │      ├── agent prompt/system overhead
                    │      ├── context / cache processing
                    │      ├── provider adapter behavior
                    │      └── response-header timeout / retry
                    │
                    └── E. Concurrent request contention
                           ├── multiple local clients
                           ├── queued requests
                           └── Ollama slot contention
\```

---

## 10.2 Investigation status

| Fault hypothesis | Status | Evidence |
|---|---|---|
| Clash/proxy blocks local Ollama | **Mostly eliminated** | Direct \`NO_PROXY\` test still showed OpenCode timeouts |
| WSL localhost networking fundamentally broken | **Mostly eliminated** | Direct \`localhost:11434\` API calls work |
| Ollama model cannot run | **Eliminated** | Direct API requests complete |
| Qwen3.5 tool calling is broken | **Mostly eliminated** | Tool call tests succeeded |
| GPU-related software bug | **Eliminated as root cause** | This is a CPU-only system, but CPU inference works normally |
| Severe swap thrashing | **No evidence** | Swap remained around 1–2 MB in observed service state |
| Local CPU is slow | **Confirmed as contributing factor** | ~5.5 tok/s generation |
| OpenCode agent/context overhead | **Highly likely contributor** | ~8.9K token accounting, large cache-read component |
| OpenCode response-header timeout/retry | **Confirmed** | Multiple exact 300s timeouts |
| Generation itself is the main cause | **Not supported** | Successful responses begin after long waits; output generation is comparatively short |
| LiteLLM caused the historical OpenCode slowdown | **Eliminated** | LiteLLM was installed only after those tests |
| Multiple-client Ollama contention | **Open hypothesis** | Later \`lsof/ss\` found LiteLLM connections, but those were created after the historical benchmarks |

---

# 11. Why \`--variant none\` helped but did not solve the problem

Comparing:

\```text
Build default variant       ≈ 13m39s
Build --variant none        ≈  7m40s
\```

shows that disabling the default reasoning variant can materially reduce latency.

But it does **not** eliminate the fundamental issue:

\```text
--variant none
      ↓
still has very long pre-response latency
      ↓
still can hit 300s header timeout
\```

The exported Plan session also contained a tiny reasoning part even though the accounting reported \`reasoning: 0\`. Therefore it is more accurate to say:

> \`--variant none\` removes the large/default reasoning mode from the benchmark, but it does not imply literally zero internal reasoning activity.

---

# 12. Why the network is no longer the main suspect

The direct comparison is especially useful:

\```text
curl → http://localhost:11434/v1
        ↓
~14.9 seconds
        ↓
success

OpenCode → same localhost Ollama service
        ↓
first attempt can wait 300 seconds
        ↓
ProviderHeaderTimeoutError
        ↓
retry
        ↓
eventual success
\```

And explicitly setting:

\```bash
NO_PROXY=localhost,127.0.0.1,::1
\```

did not remove the OpenCode timeout.

Therefore the remaining investigation should be concentrated on the **OpenCode → AI SDK / provider → Ollama request lifecycle**, rather than continually changing the WSL networking configuration.

---

# 13. LiteLLM discovery — important timeline correction

After the OpenCode / Ollama performance tests were completed, LiteLLM was installed for a **separate architecture experiment**.

Therefore:

> **LiteLLM must not be blamed for the historical OpenCode latency.**

After its installation, the following was observed:

\```text
127.0.0.1:47934 → 127.0.0.1:11434
127.0.0.1:47380 → 127.0.0.1:11434

process:
litellm PID 6133
\```

This proves that LiteLLM is currently connected to Ollama, but it does **not** prove that it was involved in the earlier slow OpenCode tests.

The current LiteLLM connections are therefore a **new-state observation**, not historical root-cause evidence.

---

# 14. Separate architecture experiment: Gemini CLI + LiteLLM + local Qwen

The purpose of the new architecture is not merely to “make OpenCode faster”.

The more strategic goal is:

> **Local-first inference with cloud escalation.**

Conceptual architecture:

\```text
                         User
                           │
                           ▼
                    ┌──────────────┐
                    │  Gemini CLI  │
                    │ Agent / UI   │
                    └──────┬───────┘
                           │
                           ▼
                   ┌────────────────┐
                   │ Model Router   │
                   │    LiteLLM     │
                   └───────┬────────┘
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
    ┌─────────────────┐         ┌──────────────────┐
    │ Local Qwen3.5-9B│         │ Cloud Gemini /   │
    │ Ollama          │         │ stronger LLM     │
    │ Private / cheap │         │ reasoning        │
    └─────────────────┘         └──────────────────┘
\```

The desired routing policy is:

\```text
                    User request
                         │
                         ▼
                  Task classification
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          Simple       Hybrid      Complex
             │           │           │
             ▼           ▼           ▼
          Qwen       Qwen first    Gemini
                         │
                         ▼
                  confidence check
                         │
                 insufficient confidence
                         │
                         ▼
                       Gemini
\```

---

# 15. Recommended task routing

## 15.1 Local Qwen is suitable for

Examples:

- explaining a small C/C++ function;
- summarizing a log;
- reading and summarizing a Markdown file;
- transforming text into a table;
- answering straightforward domain questions;
- simple grep / awk / shell reasoning;
- first-pass documentation analysis.

These tasks benefit from:

\```text
low cost
local privacy
no cloud round trip
acceptable reasoning depth
\```

## 15.2 Cloud LLM is suitable for

Examples:

- complex crash investigation;
- multi-file architectural reasoning;
- large-scale code design;
- difficult Broadcom Tomahawk 6 / FBOSS investigations;
- complicated debugging with many interacting modules;
- high-stakes engineering decisions requiring stronger reasoning.

## 15.3 Hybrid tasks

The most interesting pattern is:

\```text
Local Qwen
   ↓
First-pass investigation
   ↓
Hypotheses / evidence / confidence
   ↓
confidence < threshold
   ↓
Cloud LLM
   ↓
deep investigation
\```

This lets the local model act as a **cheap preliminary investigator** rather than trying to be a full replacement for a stronger cloud model.

---

# 16. Recommended separation of responsibilities

LiteLLM should primarily be treated as:

> **Model Gateway / Model Router**

rather than as the primary agent itself.

A clean separation is:

\```text
Agent / CLI
    │
    ▼
Model Gateway
    │
    ├── local Qwen
    ├── other local models
    ├── Gemini
    ├── GLM
    └── other approved models
\```

This keeps the agent layer independent from the model vendor.

In the future, the architecture can evolve from:

\```text
Gemini CLI → LiteLLM → Qwen
\```

to:

\```text
Gemini CLI
   ↓
Routing policy
   ↓
LiteLLM
   ├── Qwen3.5-9B
   ├── larger local model
   ├── Gemini
   ├── GLM
   └── other enterprise-approved models
\```

---

# 17. OpenCode vs. Gemini CLI + LiteLLM: current research position

These should be treated as **two separate experiments**.

## Experiment A — OpenCode + Ollama

Goal:

> Understand why a local coding-agent workflow has extremely high first-response latency and determine whether it can be improved sufficiently for practical use.

Current conclusion:

\```text
Direct Ollama           → ~14–15s tiny request
OpenCode agent          → minutes
                     ↓
Header timeout/retry + agent/context overhead
                     ↓
Main investigation target
\```

## Experiment B — Gemini CLI + LiteLLM + Qwen

Goal:

> Build a practical local-first / cloud-escalation workflow where inexpensive local inference handles simple work and stronger cloud inference handles complex work.

Current status:

**Architecture concept only; end-to-end performance has not yet been benchmarked.**

---

# 18. Recommended next experiments

The next experiments should avoid repeating long 5–15 minute tests until the request lifecycle is better understood.

## Priority 1 — isolate OpenCode provider overhead

Compare:

\```text
curl → Ollama /v1
       ↓
AI SDK / OpenAI-compatible client
       ↓
OpenCode minimal invocation
       ↓
OpenCode build/plan agent
\```

The purpose is to identify exactly where the additional tens of seconds/minutes appear.

## Priority 2 — inspect request context

Measure, as precisely as tooling permits:

- system prompt size;
- tool definitions;
- agent prompt size;
- conversation history;
- cached prefix;
- actual Ollama runtime context;
- request arrival time at Ollama;
- first token / first header time;
- generation time.

## Priority 3 — only then investigate concurrency

When multiple local AI applications are running, inspect:

\```bash
ss -tnp | grep 11434
sudo lsof -nP -iTCP:11434 -sTCP:ESTABLISHED
\```

A connection alone does **not** mean active inference. Correlate connections with Ollama logs and request timestamps.

## Priority 4 — benchmark the new routing architecture

Create a small fixed benchmark set:

| Task class | Example | Expected route |
|---|---|---|
| Simple | Explain a function | Qwen |
| Simple | Summarize a log | Qwen |
| Medium | Analyze one module | Qwen first |
| Medium | Debug several related files | Hybrid |
| Complex | Cross-module architecture design | Cloud |
| Complex | Difficult ASIC/FBOSS debugging | Cloud |

Then measure:

\```text
Latency
Success rate
Cost
Context size
Tool-use success
Human acceptance
\```

---

# 19. Operational notes / reproducibility

## Versions

\```text
Windows 11
WSL 3.0.1.0
WSL2
Ubuntu 24.04.4
Kernel 6.18.40.1-1

Ollama 0.35.1
OpenCode 1.18.34
oh-my-opencode-slim 2.2.20

Node.js v24.21.0
npm/npx 12.1.0
\```

## OpenCode benchmark pattern

For clean provider/agent experiments:

\```bash
opencode run --pure \
  --model ollama/qwen3.5:9b-opencode \
  --agent plan \
  --variant none \
  "Say exactly: TEST_STRING"
\```

Debug mode:

\```bash
opencode run \
  --pure \
  --print-logs \
  --log-level DEBUG \
  --model ollama/qwen3.5:9b-opencode \
  --agent plan \
  --variant none \
  "Say exactly: TEST_STRING"
\```

Direct local-network control:

\```bash
env NO_PROXY="localhost,127.0.0.1,::1" \
    no_proxy="localhost,127.0.0.1,::1" \
    opencode run ...
\```

---

# 20. Current root-cause assessment

### High confidence

1. **OpenCode has a request/response-header timeout problem in this local-agent configuration.**
2. **The five-minute timeout is real and is followed by retries.**
3. **Direct Ollama inference does work.**
4. **CPU-only inference is a real performance limitation.**
5. **LiteLLM did not cause the historical slowdown because it was installed later.**

### Medium confidence

6. **Agent prompt/context/tool overhead is a major contributor.**
7. **Prefill/cache processing before first token is likely a major contributor.**
8. **Model/context size interacts strongly with the CPU-only environment.**

### Still open

9. **Whether another local client was concurrently using Ollama during some slow runs.**
10. **Exactly which layer inside the OpenCode → AI SDK → Ollama pipeline accounts for the long successful-request delay.**
11. **Whether a different OpenCode configuration/model/provider adapter can reduce the pre-response latency enough for practical local coding-agent use.**

---

# 21. Key architectural conclusion

The investigation suggests that two different questions should not be conflated.

### Question A

> Can a 9B local model run useful AI coding tasks on this WSL/CPU machine?

**Yes.** Direct Ollama tests and tool calling demonstrate that the model is functional.

### Question B

> Is this machine currently an efficient platform for a full OpenCode coding-agent workflow using that model?

**Not yet demonstrated.** The multi-minute first-response behavior makes the current configuration unsuitable for comfortable interactive use.

This leads to a more useful architecture principle:

> **Use the local 9B model as a low-cost, private, fast-enough worker for suitable tasks rather than requiring it to serve as the universal agent brain.**

That principle naturally leads to the **Local-First / Cloud-Escalation** architecture.

---

# 22. Relationship to Funny Tutor

Although this investigation started from coding-agent performance, the architecture is directly relevant to the Funny Tutor project.

Funny Tutor will likely need different model tiers:

\```text
                    Funny Tutor AI Runtime
                              │
                     ┌────────┴────────┐
                     │ Model Router    │
                     └────────┬────────┘
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        Local small       Local larger       Cloud
        model             model              LLM
             │                │                │
        extraction         reasoning         hard reasoning
        classification     diagnosis         planning
        tagging            summarization     multimodal reasoning
        first pass         local RAG         high-quality lesson
\```

This makes model routing a potentially reusable platform capability for:

- domain knowledge extraction;
- question classification;
- wrong-answer diagnosis;
- resource ranking;
- learner-state updates;
- lesson planning;
- multimodal generation;
- difficult reasoning and verification.

The same **local-first / cloud-escalation** principle can therefore become part of Funny Tutor's long-term AI runtime architecture.

---

# 23. Final status — 2026-10-04

\```text
                    LOCAL AI INVESTIGATION
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
         OpenCode           Ollama           Routing
             │                │                │
         Investigated      Verified          New path
             │                │                │
       slow first response  ~5.5 tok/s      LiteLLM
       header timeout       CPU-only          +
       retry behavior      functional       Gemini CLI
             │                                 │
             ▼                                 ▼
      root cause still                    next experiment
      partly open                         local-first/cloud
\```

The most important next engineering objective is now:

> **Keep the OpenCode/Ollama investigation as a performance baseline, while independently validating Gemini CLI + LiteLLM + Qwen as a practical local-first/cloud-escalation workflow.**

---

# 24. References

## OpenCode / Ollama

- Ollama OpenCode integration: https://github.com/ollama/ollama/blob/main/docs/integrations/opencode.mdx
- Ollama context-length guidance: https://github.com/ollama/ollama/blob/main/docs/context-length.mdx
- OpenCode providers: https://dev.opencode.ai/docs/providers/
- OpenCode CLI: https://dev.opencode.ai/docs/cli/
- OpenCode agents: https://dev.opencode.ai/docs/agents/

## Related OpenCode issue references used during investigation

- https://github.com/anomalyco/opencode/issues/26602
- https://github.com/anomalyco/opencode/issues/46506

These issue references are supporting evidence / context only; they are not treated as proof of the specific root cause on this machine.

---

## Change log

### 2026-10-04

- Consolidated the OpenCode + Ollama performance investigation.
- Added complete WSL / OpenCode / Ollama deployment architecture.
- Added direct Ollama and OpenCode benchmark tables.
- Added response-header timeout evidence and session timing analysis.
- Added fault tree and root-cause status.
- Explicitly recorded that LiteLLM was installed **after** the historical slow tests and therefore is not their cause.
- Added the proposed Gemini CLI + LiteLLM + Qwen local-first/cloud-escalation architecture.
- Defined the next benchmark and investigation steps.
