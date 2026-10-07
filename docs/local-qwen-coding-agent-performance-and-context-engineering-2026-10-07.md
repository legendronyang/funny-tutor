# Funny Tutor — Local Qwen Coding-Agent Runtime: Context Engineering, Performance Tests & Fault Isolation

> Document date: 2026-10-07  
> Repository: legendronyang/funny-tutor  
> Purpose: Persist the investigation state for turning local Qwen3.5:9B into an efficient coding agent, with emphasis on long-context efficiency, low-entropy context handoff, structured tool calling, reproducible benchmarking, and fault isolation.


## 0. Session handoff — decisive state as of 2026-10-07

### 0.1 Core problem this session is solving

The engineering objective is to turn local **Qwen3.5:9B** into a practical coding agent for the remaining funny-tutor work on the current CPU-only WSL environment.

The investigation is not merely about raw model speed. The actual optimization target is:

> **Maximize useful coding work per unit wall-clock time by minimizing context inflation, avoiding unnecessary model/runner reloads, preserving structured tool calling, and maintaining a deterministic low-entropy task state.**

The session therefore treats the Agent Runtime as a systems stack:

~~~text
Agent Runtime
    ↓
request construction / context compilation
    ↓
protocol translation
    ↓
LiteLLM
    ↓
Ollama runner
    ↓
Qwen3.5:9B
    ↓
tool execution / next turn
~~~

A central methodological rule is:

> **Never attribute an Agent-level failure to Qwen until the equivalent lower-level model and protocol path has been independently validated.**

### 0.2 Test scenario map

| Scenario | Purpose | Result |
|---|---|---|
| Direct Ollama, Qwen3.5:9B, warm, 16K, think=false | Establish raw model baseline | PASS; ~2.18 s tiny prompt |
| Direct Ollama structured tool call | Verify Qwen can emit native tool calls | PASS |
| LiteLLM OpenAI-compatible route | Verify routing, text, tool calling, streaming, and parameter propagation | PASS |
| LiteLLM Gemini-native route | Verify Gemini-compatible text/function calling/AUTO/streaming | PASS |
| Gemini CLI Agent Runtime | Measure real context injection, transport behavior, and actual tool execution | Context inflation confirmed; pseudo-tool problem remains unresolved |

### 0.3 Evidence hierarchy

**Level A — direct model/runtime facts**

- Qwen3.5:9B + Ollama + 16K works.
- Native structured tool calling works.
- CPU generation is approximately 6 tok/s in the observed environment.
- Full prompt prefill is approximately 37 tok/s in the measured 2026-10-07 curve.

**Level B — protocol facts**

- LiteLLM OpenAI-compatible text/tool/streaming works.
- LiteLLM Gemini-native text/functionCall/AUTO/streaming works.
- num_ctx=16384 propagates to Ollama on the OpenAI-compatible path.
- The same num_ctx does not propagate on the Gemini-native path.

**Level C — Agent Runtime facts**

- Gemini CLI injects a large generic system instruction.
- Exact captured baseline request: systemInstruction 21,434 chars; contents 1,785 chars; tools 637 chars.
- Removing thinkingConfig does not change the downstream Gemini replay promptTokenCount: both are 2050.
- Gemini CLI read_file still produces pseudo-tool text instead of a structured tool execution event.

### 0.4 Current architecture finding

The most important architectural mismatch currently observed is:

~~~text
Gemini CLI model semantics:
    gemini-2.5-pro
        + Gemini-specific generationConfig
        + thinkingBudget=8192

              ↓

LiteLLM alias:
    gemini-2.5-pro → local-qwen

              ↓

Actual execution:
    Qwen3.5:9B via Ollama
~~~

Therefore a single model identifier is simultaneously being interpreted as:

1. a Gemini CLI model profile, and
2. a LiteLLM routing alias to a local Qwen model.

This is a configuration-semantics mismatch and should be treated as an architectural risk even though it is not the demonstrated cause of the 2050-token truncation.

### 0.5 Current low-entropy state

~~~yaml
objective: turn local Qwen3.5:9B into an efficient coding agent
repo: /home/ronyang/workspace/funny-tutor
model: qwen3.5:9b
model_alias_in_cli: gemini-2.5-pro
ollama_context_control:
  openai_compatible: 16384
  gemini_native: not propagated; Ollama runner observed at 4096
thinking:
  gemini_cli_baseline: enabled, thinkingBudget=8192
  no_thinking_replay: removed from generationConfig
tools:
  read_file: declared and translated to Ollama tools on Gemini-native path
skills:
  disabled_for_controlled_cli_test
retries:
  retryFetchErrors: false
  maxAttempts: 1

settled:
  - Qwen native tool calling works
  - LiteLLM OpenAI tool calling works
  - LiteLLM Gemini-native function calling works
  - Gemini-native AUTO function calling works
  - Gemini-native tools schema reaches Ollama
  - Gemini-native path drops num_ctx=16384
  - Ollama truncates a 5655-token request to an effective 2050-token input with a 4096 runner
  - the 12:27 OpenAI control request really used a 16384 runner
  - its ~80 s latency was dominated by cold 16384 runner/model load + 326 generated reasoning tokens
  - removing thinkingConfig did not change promptTokenCount=2050 on Gemini-native replay

open:
  - exact root cause of Gemini CLI 'fetch failed'
  - exact cause of Gemini CLI pseudo-tool output
  - whether Gemini CLI can be made to use the OpenAI-compatible LiteLLM route cleanly
  - whether a thin Python Agent Runtime should replace Gemini CLI
~~~

## 1. Executive summary

The original goal was to turn the local Qwen3.5:9B model into a practical coding agent for the remaining work in funny-tutor.

The investigation started from:

~~~text
OpenCode → Ollama → qwen3.5:9b-opencode
~~~

because OpenCode was much slower than direct Ollama inference.

The current alternative under evaluation is:

~~~text
Python task/orchestration layer
        ↓
Gemini CLI (Agent Runtime)
        ↓
LiteLLM Proxy / Router
        ↓
Ollama
        ↓
Qwen3.5:9B
~~~

The most important result is that the underlying local model stack is technically viable:

- Direct Ollama + Qwen3.5:9B + 16K + warm runner + think=false: PASS, about 2.18 s for a tiny baseline.
- Native Ollama structured tool calling: PASS.
- LiteLLM OpenAI-compatible text and tool calling: PASS.
- LiteLLM Gemini-native text and function calling, including AUTO and streaming: PASS.
- Gemini CLI simple text request: FAIL/intermittent at the fetch layer; a single-attempt test still waited about 62 s before fetch failure.
- Gemini CLI read_file task: Qwen produces a semantic/pseudo tool call as ordinary text, while Gemini CLI reports tool_calls=0; no real structured tool execution occurs.
- Explicitly disabling Agent Skills did not fix the tool-calling problem, so Skills are no longer the leading root cause.
- The current investigation has therefore converged on two Gemini CLI-specific questions:
  1. Why does the first HTTP fetch/request path fail only after roughly 60–62 s?
  2. Why does the exact Gemini CLI request cause Qwen to emit pseudo-tool text instead of a structured functionCall, even though the manually constructed Gemini-native request succeeds?

This document records tested facts separately from unresolved hypotheses so future sessions can resume without repeating settled experiments.

## 2. Runtime and hardware topology

### 2.1 Host environment

~~~text
Windows 11
  │
  ├─ WSL2
  │    └─ Ubuntu 24.04.4
  │         ├─ Intel i5-11400, 6C/12T
  │         ├─ about 15 GiB RAM visible in WSL
  │         └─ about 4 GiB swap
  │
  └─ Clash Verge v2.4.7
~~~

Additional observations:

- Node.js: v24.21.0
- npm/npx: 12.1.0
- WSLg: 1.0.79
- WSL kernel observed: 6.18.40.1-1
- Windows build observed: 10.0.26300.9550
- WSL disk: roughly 1 TB virtual disk, with only tens of GB used during this work
- Ollama: 0.35.1
- OpenCode: 1.18.34

### 2.2 Ollama model inventory

Two distinct 6.6 GB model entries exist:

~~~text
qwen3.5:9b-opencode
qwen3.5:9b
~~~

Important benchmark rule:

- qwen3.5:9b-opencode was observed/configured for 64K context.
- qwen3.5:9b initially defaulted to 4K context.
- Current controlled tests use qwen3.5:9b with 16K context.

These are different model entries/runners. Loading one while testing the other can create a model-switch/load penalty and invalidate latency comparisons.

## 3. Historical OpenCode baseline

The historical local coding-agent path was:

~~~text
OpenCode
  ↓
oh-my-opencode-slim / agent routing
  ↓
ollama/qwen3.5:9b-opencode
  ↓
Ollama
  ↓
CPU inference
~~~

Representative diagnostic command:

~~~bash
opencode run --pure --print-logs --log-level DEBUG \
  --model ollama/qwen3.5:9b-opencode \
  --agent build \
  --variant none \
  "Say exactly: OPENCODE_DEBUG_OK"
~~~

Observed timing examples:

- qwen3.5:9b-opencode through OpenCode with variant none: about 7 min 40 s in one controlled run.
- An earlier equivalent run: about 13 min 39 s.
- Direct Ollama earlier showed about 14 s in a configuration that included model loading.
- A later warm, controlled 16K direct Ollama run was only about 2.18 s.

This led to the key change in investigation strategy:

> Stop broadly investigating “why is OpenCode slow?” and instead measure the complete agent stack layer by layer, then maximize effective Qwen coding-agent throughput on the existing hardware.

## 4. Current alternative architecture

The intended prototype is:

~~~text
                 +---------------------------+
                 | funny-tutor task          |
                 | orchestrator              |
                 | future Python             |
                 +-------------+-------------+
                               |
                               v
                 +---------------------------+
                 | Gemini CLI                |
                 | Agent Runtime under test  |
                 +-------------+-------------+
                               |
                         Gemini-compatible
                           API requests
                               |
                               v
                 +---------------------------+
                 | LiteLLM :4000             |
                 | alias / routing / proxy   |
                 +-------------+-------------+
                               |
                               v
                 +---------------------------+
                 | Ollama :11434             |
                 +-------------+-------------+
                               |
                               v
                 +---------------------------+
                 | Qwen3.5:9B                |
                 | CPU inference             |
                 +---------------------------+
~~~

The eventual fallback architecture being considered is:

~~~text
Python Agent Runtime
        ↓
LiteLLM
        ↓
Ollama
        ↓
Qwen3.5:9B
~~~

with an explicit Python tool loop and a compact persistent task-state/context compiler.

## 5. LiteLLM configuration

Systemd service:

~~~ini
[Service]
User=ronyang
WorkingDirectory=/home/ronyang/gemini-proxy
ExecStart=/home/ronyang/gemini-proxy/.venv/bin/litellm \
  --config /home/ronyang/gemini-proxy/litellm_config.yaml \
  --port 4000
Restart=always
RestartSec=5
~~~

Service is active and listens on port 4000.

Representative routing configuration:

~~~yaml
model_list:
  - model_name: local-qwen
    litellm_params:
      model: ollama_chat/qwen3.5:9b
      api_base: "http://localhost:11434"
      num_ctx: 16384

  - model_name: cloud-gemini
    litellm_params:
      model: gemini/gemini-3.8-flash
      api_key: "os.environ/REAL_GEMINI_API_KEY"

router_settings:
  model_group_alias:
    "gemini-3.5-flash": "local-qwen"
    "gemini-2.5-pro": "local-qwen"
    "gemini-3.8-flash": "cloud-gemini"
    "gemini-3.5-flash-lite": "local-qwen"
    "gemini-3.1-pro-preview": "local-qwen"
~~~

Fallback from local-qwen to cloud-gemini was deliberately disabled during benchmarking, so local failures cannot be silently masked by cloud inference.

## 6. Gemini CLI configuration

Current project settings:

~~~json
{
  "tools": {
    "core": ["read_file"]
  },
  "skills": {
    "enabled": false
  },
  "general": {
    "retryFetchErrors": false,
    "maxAttempts": 1
  }
}
~~~

Interpretation:

- Only read_file is allowed among the selected built-in tools.
- Agent Skills are disabled for the controlled test.
- Retry of fetch errors is disabled.
- Maximum model attempt is one, making transport failures measurable without retry/backoff contamination.
- Runtime uses YOLO approval mode so approval prompts do not add interactive overhead.

A project-level .gemini/skills symlink had previously been deleted, but user/global skills were still discovered under ~/.agents/skills. This motivated the explicit skills.enabled=false A/B test.

## 7. Captured Gemini CLI system prompt

With GEMINI_WRITE_SYSTEM_MD=1, Gemini CLI successfully generated:

~~~text
.gemini/system.md
38 KB
295 lines
~~~

The capture shows a substantial software-engineering Agent Runtime prompt, including:

- Core mandates
- Untrusted-data handling
- Project convention rules
- Library/framework verification
- Style/structure rules
- Proactiveness
- Ambiguity/expansion handling
- Skill guidance
- Available Agent Skills

Earlier captures included many user skills under ~/.agents/skills, such as:

~~~text
using-agent-skills
test-driven-development
spec-driven-development
source-driven-development
planning-and-task-breakdown
security-and-hardening
performance-optimization
documentation-and-adrs
debugging-and-error-recovery
...
~~~

This is evidence that Gemini CLI is materially more than a thin CLI wrapper: it supplies system instructions, skill discovery, tools, session state, and a model communication/runtime layer.

The captured system prompt is also an important context-engineering artifact because it gives a concrete baseline for measuring how much generic agent context is being injected into a 9B local model.

## 8. Investigation methodology

The investigation follows a strict reduction and isolation strategy:

~~~text
High-level Agent failure
        ↓
Reduce to smallest reproducible prompt
        ↓
Remove optional orchestration
        ↓
Disable Skills
        ↓
Restrict tools to one tool
        ↓
Keep target model warm
        ↓
Fix context size
        ↓
Disable thinking for raw-latency tests
        ↓
Validate native tool calling independently
        ↓
Validate LiteLLM protocol conversion independently
        ↓
Capture actual Agent-runtime request
~~~

Core rule:

> Do not attribute a high-level Agent failure to the model until the equivalent lower-level model/protocol test has passed.

Second rule:

> Do not attribute long wall-clock latency to token generation until request wait, retry, and model load are separately accounted for.

## 9. Detailed test results

### 9.1 Direct Ollama text baseline — 16K, warm

Representative request:

~~~bash
curl --no-buffer http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model":"qwen3.5:9b",
    "messages":[{"role":"user","content":"Say exactly: DIRECT_QWEN_CTX16K_OK"}],
    "stream":true,
    "think":false,
    "options":{"num_ctx":16384},
    "keep_alive":"24h"
  }'
~~~

Observed:

| Metric | Result |
|---|---:|
| Wall clock | 2.184 s |
| Ollama total_duration | ~2.177 s |
| load_duration | ~0.0023 s |
| prompt_eval_count | 24 |
| prompt_eval_cached_count | 18 |
| prompt_eval_duration | ~0.511 s |
| eval_count | 10 |
| eval_duration | ~1.540 s |
| Approx. generation rate | ~6.5 tok/s |
| Context | 16384 |
| Runner state | warm |
| Thinking | false |

Conclusion:

> 16K context by itself is not responsible for multi-minute latency. A warm Qwen3.5:9B can answer a tiny prompt in about two seconds.

### 9.2 Warm-up contamination rule

Using ollama run qwen3.5:9b with no explicit context setting can create a 4K runner because 4K is the default in the observed configuration.

For a 16K benchmark, warm through the API with:

~~~json
{
  "options": {"num_ctx": 16384},
  "keep_alive": "24h"
}
~~~

and verify with:

~~~bash
ollama ps
~~~

The runner should explicitly show 16384 context.

This matters because a runner resize or model switch can dominate a benchmark.

### 9.3 Direct Ollama structured tool calling

A native /api/chat request containing an explicit read_file tool declaration returned a real structured tool_calls array, e.g.:

~~~json
{
  "message": {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "function": {
          "name": "read_file",
          "arguments": {
            "path": "docs/domain-knowledge-learning-os-research-2026-10-03.md"
          }
        }
      }
    ]
  }
}
~~~

One observed run:

- Total: ~26.9 s
- Load: ~11.875 s
- Prompt: ~320 tokens
- Generated: ~44 tokens
- Approx. generation rate: ~6.43 tok/s

The high wall clock was associated with creation/reconfiguration of the 16K runner from an earlier 4K state.

Conclusion:

> Qwen3.5:9B + Ollama + 16K + native structured tool calling is proven viable.

This directly disproves “Qwen9B cannot call tools” as the root cause.

### 9.4 LiteLLM OpenAI-compatible text

Direct /v1/chat/completions with model=local-qwen successfully returned the requested exact string.

Usage metadata was available, including prompt/completion/total token counts.

An important observation is that this path exposed substantial reasoning_content unless thinking behavior was explicitly controlled. Therefore benchmark prompts should explicitly use the non-thinking path when measuring raw latency.

### 9.5 LiteLLM alias routing

Using model=gemini-2.5-pro successfully routed to local-qwen and returned the expected text.

Conclusion:

~~~text
gemini-2.5-pro
      ↓
local-qwen
      ↓
qwen3.5:9b
~~~

works.

### 9.6 LiteLLM OpenAI-compatible non-stream tool calling

A direct request with tool_choice forcing read_file returned a valid structured response with:

~~~text
finish_reason = tool_calls
message.tool_calls[0].function.name = read_file
~~~

and JSON arguments containing the expected file path.

Conclusion:

> LiteLLM OpenAI-compatible structured tool calling is proven.

### 9.7 LiteLLM OpenAI-compatible streaming tool calling

Streaming /v1/chat/completions also returned structured tool-call deltas followed by:

~~~text
finish_reason = tool_calls
data: [DONE]
~~~

Conclusion:

> LiteLLM streaming tool calling is proven.

### 9.8 LiteLLM Gemini-native text

A manually constructed request to:

~~~text
/v1beta/models/gemini-2.5-pro:generateContent
~~~

returned a valid Gemini-style candidates/content/parts response plus usage metadata.

Conclusion:

> Gemini-native LiteLLM text path works.

### 9.9 LiteLLM Gemini-native function calling — ANY

A Gemini-native request using tools.functionDeclarations and:

~~~json
"toolConfig": {
  "functionCallingConfig": {
    "mode": "ANY"
  }
}
~~~

returned a real functionCall with the expected tool name and arguments.

Conclusion:

> Gemini-native function calling works through LiteLLM and Qwen.

### 9.10 LiteLLM Gemini-native function calling — AUTO

A second direct test used:

~~~json
"mode": "AUTO"
~~~

and the current Gemini CLI-style parameter name file_path.

It returned:

~~~json
{
  "functionCall": {
    "name": "read_file",
    "args": {
      "file_path": "docs/domain-knowledge-learning-os-research-2026-10-03.md"
    }
  }
}
~~~

Conclusion:

> Qwen does not require forced ANY mode. Gemini-native AUTO function calling also works.

### 9.11 Gemini-native streaming function calling

The corresponding streamGenerateContent request emitted functionCall in a streaming chunk.

Conclusion:

> Gemini-native streaming structured function calling is proven at the manually constructed request level.

## 10. Gemini CLI test results

### 10.1 Simple text with retry enabled

Representative command:

~~~bash
gemini   --model gemini-2.5-pro   --approval-mode=yolo   --output-format=json   -p "Say exactly: FETCH_TEST"
~~~

Observed pattern:

1. Gemini CLI starts.
2. First request may fail with:
   TypeError: fetch failed sending request
3. With retry enabled, a later request can succeed.
4. Earlier slow runs were partly explained by the fact that qwen3.5:9b-opencode was resident while the alias needed qwen3.5:9b, causing an Ollama model switch/load.

Important correction:

> Do not attribute all early long Gemini CLI runs to context length or Qwen generation. Model identity/runner switching was one source of large latency.

### 10.2 read_file Agent with Skills enabled

The Agent test repeatedly produced ordinary text that semantically described a tool call, for example:

~~~text
我将使用 read_file 工具读取指定的文件。

read_file(file_path='docs/domain-knowledge-learning-os-research-2026-10-03.md')
~~~

Other variants included pseudo-XML or pseudo-JSON tool syntax.

Gemini CLI reported:

~~~text
tool_calls = 0
~~~

No actual read_file execution occurred.

Interpretation:

- The model understands the tool name.
- The model understands the file path argument.
- But no structured function-call event reaches Gemini CLI's tool-execution layer.

This is a protocol/Agent-runtime symptom, not evidence that Qwen lacks tool semantics.

### 10.3 read_file Agent with Skills disabled

Controlled settings:

~~~json
{
  "tools": {
    "core": ["read_file"]
  },
  "skills": {
    "enabled": false
  }
}
~~~

The test still produced pseudo-tool text and:

~~~text
tool_calls = 0
~~~

Therefore:

> Agent Skills are not the primary explanation for the structured tool-call failure.

They remain relevant to context size and future throughput optimization, but the current evidence does not support making them the main blocker.

## 11. Retry-isolation experiment

Settings were changed to:

~~~json
{
  "tools": {
    "core": ["read_file"]
  },
  "skills": {
    "enabled": false
  },
  "general": {
    "retryFetchErrors": false,
    "maxAttempts": 1
  }
}
~~~

The smallest possible prompt was then used:

~~~bash
time gemini   --model gemini-2.5-pro   --approval-mode=yolo   --output-format=json   -p "Say exactly: FETCH_TEST"
~~~

Result:

~~~text
Error when talking to Gemini API
TypeError: fetch failed sending request

real    1m2.088s
user    0m1.770s
sys     0m0.336s
~~~

Crucially, there was no retry message.

Therefore:

> The ~62 s delay is not explained by Gemini CLI retry/backoff. The first fetch/request path itself is waiting for roughly one minute before failing.

This is a decisive isolation result.

## 12. Current failure tree

~~~text
Local Qwen Coding Agent
│
├── A. Raw model inference
│   ├── Qwen CPU inference too slow?
│   │     └── NOT primary blocker
│   │          Evidence: warm direct Ollama tiny prompt ≈ 2.18 s
│   │
│   ├── 16K inherently too slow?
│   │     └── NOT proven; tiny warm 16K request is fast
│   │
│   └── Qwen cannot tool-call?
│         └── FALSE
│              Evidence: Ollama native tool_calls PASS
│
├── B. Ollama
│   ├── Model loading/switching
│   │     └── REAL benchmark-noise source
│   │          qwen3.5:9b and qwen3.5:9b-opencode are distinct
│   │
│   └── Warm 16K runner
│         └── PASS
│
├── C. LiteLLM
│   ├── Model alias routing
│   │     └── PASS
│   ├── OpenAI text
│   │     └── PASS
│   ├── OpenAI tool calling
│   │     └── PASS
│   ├── OpenAI streaming tool calling
│   │     └── PASS
│   ├── Gemini-native text
│   │     └── PASS
│   ├── Gemini-native functionCall
│   │     └── PASS
│   ├── Gemini-native AUTO
│   │     └── PASS
│   └── Gemini-native streaming
│         └── PASS
│
├── D. Gemini CLI transport
│   ├── Simple prompt
│   │     └── FAIL/intermittent
│   ├── Retry
│   │     └── NOT primary cause
│   │          retry disabled yet ≈62 s to failure
│   └── First fetch/request
│         └── HIGH PRIORITY
│
└── E. Gemini CLI Agent protocol
    ├── Skills
    │     └── NOT primary cause
    ├── Tool semantics understood by Qwen
    │     └── YES
    ├── Structured functionCall from CLI path
    │     └── FAIL
    └── Pseudo-tool ordinary text
          └── REPEATED
~~~

## 13. Settled conclusions vs unresolved hypotheses

### 13.1 Strongly established

1. Qwen3.5:9B can perform structured tool calling.
2. Qwen3.5:9B can run at 16K context in the current Ollama environment.
3. Warm 16K direct inference for tiny prompts is about 2.18 s.
4. LiteLLM OpenAI-compatible tool calling works.
5. LiteLLM streaming tool calling works.
6. LiteLLM Gemini-native function calling works.
7. Gemini-native AUTO function calling works in the manually constructed request.
8. Gemini-native streaming function calling works.
9. Gemini CLI can fail with fetch failed even for the simplest prompt.
10. The single-attempt retry-disabled test still took about 62 s to fail; retry/backoff is therefore not the root cause of that delay.
11. Disabling Agent Skills did not fix the Gemini CLI structured-tool failure.

### 13.2 Unresolved

#### Exact cause of fetch failed

Still unknown whether the problem is:

~~~text
Gemini CLI
 → Node/Undici fetch
 → Base URL resolution
 → localhost/127.0.0.1 behavior
 → HTTP proxy environment
 → LiteLLM socket/HTTP lifecycle
 → other transport condition
~~~

The underlying error should be extracted from the Gemini CLI error-report JSON. Useful fields include:

~~~text
code
errno
syscall
address
port
cause
message
~~~

Potential signatures include ECONNREFUSED, ETIMEDOUT, ECONNRESET, DNS/proxy-related errors, or another transport-layer cause.

#### Exact Gemini CLI request payload

The manually constructed Gemini-native request succeeds, but the exact request emitted by Gemini CLI has not yet been captured and compared field-by-field.

Most important fields:

~~~text
systemInstruction
contents
tools
toolConfig
generationConfig
thinkingConfig
response-format parameters
~~~

The key question is:

> What does Gemini CLI actually send that differs from the known-good hand-built Gemini-native request?

#### Cause of pseudo-tool output

The model is clearly capable of emitting a functionCall in a correctly shaped request, but the Gemini CLI path causes ordinary tool-like text.

The leading hypothesis is therefore:

~~~text
Gemini CLI request semantics
        ≠
known-good manually constructed Gemini-native request
~~~

rather than:

~~~text
Qwen cannot use tools
~~~

## 14. Secondary findings that should not be confused with the main blocker

### 14.1 Gemini CLI token statistics are not reliable for current accounting

Gemini CLI often reported:

~~~text
total_tokens = 0
input_tokens = 0
output_tokens = 0
~~~

while direct LiteLLM calls exposed normal usage metadata.

Therefore performance work should use:

- wall-clock time
- Ollama load_duration
- Ollama total_duration
- prompt/eval counts
- direct LiteLLM usage
- explicit tool event counts

Do not infer Qwen throughput from the Gemini CLI zero-token field.

### 14.2 Missing ripgrep is secondary

Gemini CLI repeatedly warns:

~~~text
Ripgrep is not available. Falling back to GrepTool.
~~~

This is worth fixing eventually, but it cannot explain the ~62 s fetch failure.

### 14.3 True-color and duplicate YOLO warnings are benign for this investigation

Warnings such as:

~~~text
True color (24-bit) support not detected.
YOLO mode is enabled. All tool calls will be automatically approved.
~~~

are not currently correlated with the long delay.

### 14.4 cleanup_ops metrics warnings are instrumentation noise

Startup messages such as:

~~~text
Phase 'cleanup_ops' was started but never ended.
Cannot measure phase 'cleanup_ops'
~~~

are telemetry/metrics anomalies. There is no evidence that they consume the observed 60+ seconds.

### 14.5 Gemini-native LiteLLM context propagation — now experimentally localized

The downstream request capture proves that the Gemini-native path sent model=qwen3.5:9b, stream=false, think=null, keep_alive=null, and only temperature/top_p in options; num_ctx was absent. Ollama therefore ran the request with a 4096-context runner and logged truncating input prompt with limit=2050, prompt=5655, new=2050.

A matched OpenAI-compatible control request sent options.num_ctx=16384, and Ollama subsequently launched llama-server with -c 16384 and initialized n_ctx_slot=16384.

Conclusion:

> The missing 16K context is not a generic LiteLLM configuration failure; it is specific to the Gemini-native → Ollama translation path observed in this environment/version.

The same capture also proves that the Gemini-native path translates the read_file tool schema successfully.

### 14.6 LiteLLM had a non-blocking logging issue

A successful Gemini-native request produced a non-blocking success/logging error similar to:

~~~text
[Non-Blocking] LiteLLM.Success_Call Error:
Google GenAI Generate Content: httpx_response is None
~~~

The HTTP request itself returned 200 with valid content.

Classify this as an observability problem, not a request correctness failure.

## 15. Quantitative latency model

For an Agent request:

~~~text
T_total =
    T_CLI startup
  + T_transport_connect
  + T_transport_wait/failure
  + T_LiteLLM routing
  + T_Ollama load/switch
  + T_prompt_eval
  + T_model_generation
  + T_tool_execution
  + T_followup_model_turns
~~~

The current tests demonstrate that these terms can differ by orders of magnitude.

Latest replay/control evidence:

~~~text
Gemini-native replay:
  downstream prompt = 5655 tokens
  Ollama effective prompt = 2050 tokens
  cached prefix = 2046 tokens
  measured request ≈ 8.49 s

OpenAI-compatible control:
  input = 17 tokens
  runner creation/load ≈ 23.5 s
  prompt eval ≈ 0.90 s
  generation = 326 tokens at ≈ 5.98 tok/s
  total ≈ 79.96 s
~~~

The ~62 s Gemini CLI fetch-failure experiment remains a separate transport symptom; it must not be conflated with the ~80 s OpenAI-compatible Qwen generation/load experiment.

Warm direct Qwen:

~~~text
T_total ≈ 2.18 s
load ≈ 0
generation ≈ 1.54 s
~~~

Engineering implication:

> Effective coding-agent throughput is a systems problem, not only a model-size problem.

## 16. Context engineering direction

The long-term target is not to keep reinjecting the entire conversation or generic Agent system prompt.

Desired pipeline:

~~~text
Raw conversation/history
        ↓
State extraction
        ↓
Persistent task state
        ↓
Relevant repository evidence
        ↓
Minimal action context
        ↓
Qwen decision
        ↓
Structured tool call
        ↓
Compact tool result
        ↓
Updated state
~~~

Core principle:

> Persist state once; retrieve only the minimum state needed for the next decision.

For coding work, a compact state should preserve:

~~~text
Goal
Scope and constraints
Repository state
Relevant files
Known failures
Tests already run
Observed outputs
Settled decisions
Open hypotheses
Next experiment/action
Success/failure criteria
~~~

This enables low-entropy handoff between ChatGPT, Python orchestration, Gemini CLI if retained, and Qwen without repeatedly reconstructing the entire conversation.

## 17. Candidate persistent Agent state

Conceptual format:

~~~yaml
task_id: ...
goal: ...
scope:
  include: [...]
  exclude: [...]

repository:
  root: ...
  branch: ...
  relevant_files: [...]

environment:
  model: qwen3.5:9b
  context: 16384
  tools: [read_file]
  skills: false

evidence:
  - observation: ...
    source: ...
    confidence: proven

decisions:
  - statement: ...
    confidence: proven

hypotheses:
  - statement: ...
    status: open

tests:
  - name: ...
    result: pass|fail
    timing: ...
    interpretation: ...

next_action:
  objective: ...
  command: ...
  expected_signal: ...
~~~

This should become the basis of a future context compiler/state manager rather than relying on raw transcript replay.

## 18. Recommended next diagnostic sequence

### Step 1 — Extract the underlying fetch error

Inspect the most recent Gemini CLI error-report JSON under /tmp/gemini-client-error-*.json and extract only:

~~~text
code
errno
syscall
address
port
cause
message
~~~

Goal: identify the actual transport failure class.

### Step 2 — Verify Gemini CLI endpoint and proxy environment

Inspect only non-secret variables:

~~~bash
env | grep -E '^(GOOGLE_GEMINI_BASE_URL|GOOGLE_GENAI_API_VERSION|GEMINI_MODEL|HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|NO_PROXY)='
~~~

Also compare:

~~~bash
curl -sS http://127.0.0.1:4000/v1/models
curl -sS http://localhost:4000/v1/models
~~~

Goal: isolate endpoint, localhost, DNS, IPv4/IPv6, or proxy effects.

### Step 3 — Observe LiteLLM during the minimal Gemini CLI request

Terminal A:

~~~bash
sudo journalctl -u litellm -f
~~~

Terminal B:

~~~bash
time gemini   --model gemini-2.5-pro   --approval-mode=yolo   --output-format=json   -p "Say exactly: FETCH_TEST_2"
~~~

Critical discriminator:

- If LiteLLM receives nothing during the ~62 s wait, the fault is above LiteLLM: Gemini CLI / Node fetch / endpoint / proxy.
- If LiteLLM receives the request immediately, investigate LiteLLM and the downstream Ollama call.

### Step 4 — Test Node fetch directly

Because Gemini CLI uses Node.js, isolate:

~~~text
Node v24.21.0
      ↓
fetch()
      ↓
127.0.0.1:4000
~~~

This separates Node/Undici behavior from Gemini CLI core logic.

### Step 5 — Capture the actual Gemini CLI request

Once transport is stable, compare the real Gemini CLI Gemini-native request to the known-good hand-built request field-by-field.

Priority fields:

~~~text
systemInstruction
contents
tools
toolConfig.functionCallingConfig
generationConfig
thinkingConfig
response formatting
~~~

This is the highest-value experiment for explaining pseudo-tool output.

### Step 6 — Only then decide the production Agent Runtime

Option A:

~~~text
Python orchestrator
 ↓
Gemini CLI
 ↓
LiteLLM
 ↓
Qwen
~~~

Option B:

~~~text
Python Agent Runtime
 ↓
Context compiler / task state
 ↓
LiteLLM
 ↓
Qwen
 ↓
explicit tool loop
~~~

Option B becomes increasingly attractive if Gemini CLI continues to impose transport instability, large generic system context, or tool-protocol incompatibility.

## 19. Architecture decision criteria

Do not select the production runtime by subjective “model quality” alone.

Measure:

~~~text
1. One-shot latency
2. Warm-turn latency
3. Context ingestion cost
4. Tool-call success rate
5. Tool-call round-trip latency
6. Retry behavior
7. Memory pressure
8. State persistence quality
9. Prompt/context size
10. Determinism/reproducibility
11. Ease of debugging
12. Security / enterprise deployability
~~~

For the target CPU-only environment, the most important metric is:

> Effective useful coding work completed per unit wall-clock time, not raw tokens/second.

## 20. Current evidence table

| Layer / scenario | Result | Evidence |
|---|---|---|
| Qwen3.5:9B raw inference | PASS | Warm direct Ollama |
| Qwen3.5:9B at 16K | PASS | Warm direct 16K test |
| Qwen structured tool call | PASS | Native Ollama tool_calls |
| LiteLLM model alias | PASS | gemini-2.5-pro → local-qwen |
| LiteLLM OpenAI text | PASS | /v1/chat/completions |
| LiteLLM OpenAI tool call | PASS | structured tool_calls |
| LiteLLM OpenAI streaming tool call | PASS | tool_calls delta + finish_reason |
| LiteLLM Gemini-native text | PASS | generateContent |
| LiteLLM Gemini-native functionCall | PASS | ANY mode |
| LiteLLM Gemini-native AUTO | PASS | functionCall returned |
| LiteLLM Gemini-native streaming | PASS | streamGenerateContent |
| Gemini CLI simple text | FAIL/intermittent | fetch failed |
| Gemini CLI simple text, retry disabled | FAIL | ~62 s before fetch failure |
| Gemini CLI read_file with Skills | FAIL | pseudo tool text, tool_calls=0 |
| Gemini CLI read_file with Skills disabled | FAIL | pseudo tool text, tool_calls=0 |

## 21. Security and reproducibility note

Live API credentials were accidentally exposed during earlier troubleshooting while inspecting the systemd service. They are deliberately excluded from this document.

The credentials should be rotated and moved to a safer secret mechanism. Future benchmark logs must also avoid printing API keys or bearer tokens.

All performance claims in this document should be treated as environment-specific measurements from the stated WSL/CPU configuration, not universal benchmarks for the model.


## 21.5. Decisive downstream capture findings — 2026-10-07

### Gemini CLI captured baseline request

Persisted capture:

~~~text
~/gemini-forensics/gemini-cli-baseline.json
~~~

Measured text sizes:

| Component | Size |
|---|---:|
| systemInstruction | 21,434 chars |
| contents | 1,785 chars |
| tools | 637 chars |
| generationConfig | Gemini CLI gemini-2.5-pro preset |
| thinkingConfig | includeThoughts=true, thinkingBudget=8192 |

A matched no-thinking capture removed thinkingConfig, but both Gemini-native replays reported:

~~~text
promptTokenCount = 2050
~~~

Therefore:

> thinkingBudget=8192 is not the demonstrated source of the 2050-token input truncation.

### Gemini-native → Ollama real request

Captured downstream request:

~~~json
{
  "model": "qwen3.5:9b",
  "stream": false,
  "think": null,
  "keep_alive": null,
  "options": {
    "temperature": 1,
    "top_p": 0.95
  },
  "message_count": 2
}
~~~

Message sizes:

~~~text
system = 21,430 chars
user   = 1,781 chars
~~~

The read_file tool schema was present downstream in standard OpenAI/Ollama function format.

No num_ctx was present.

### Ollama evidence for the Gemini-native request

Ollama logged:

~~~text
n_ctx_slot = 4096
truncating input prompt
    limit = 2050
    prompt = 5655
    new = 2050
~~~

The request then restored a cached 2046-token checkpoint and re-evaluated only 4 new prompt tokens. Consequently the observed 8.49 s replay is a cache-hit latency result, not a full 2050-token prefill benchmark.

### OpenAI-compatible control request

The matched control request used only a 30-character user prompt, but the captured downstream Ollama request contained:

~~~json
{
  "model": "qwen3.5:9b",
  "stream": false,
  "options": {
    "num_ctx": 16384
  }
}
~~~

Ollama then launched:

~~~text
llama-server ... -c 16384
llama_context: n_ctx = 16384
load_model: ... n_ctx_slot = 16384
~~~

Observed timing:

~~~text
runner/model load   ≈ 23.5 s
prompt eval         ≈ 0.90 s / 17 tokens
generation          ≈ 54.39 s / 326 tokens
generation rate     ≈ 5.98 tok/s
total               ≈ 79.96 s
~~~

The ~80 s wall clock is therefore primarily cold 16K runner/model initialization plus Qwen reasoning generation, not prompt-prefill cost.

### Decisive comparison

~~~text
                         Gemini-native          OpenAI-compatible
                         -------------          -----------------
num_ctx downstream      missing                16384
Ollama context           4096                   16384
large system prompt      yes (21.4 KB)          no
tool schema              yes                    not used in control
prompt truncation        yes: 5655 → 2050       no
Qwen function schema     preserved              not tested here
~~~

This is the current strongest protocol-level finding in the session.

## 21.6. Gemini CLI wire-protocol probe — interpretation correction

The 2026-10-07 Gemini CLI probe produced a capture at:

~~~text
~/gemini-captures/20261007-105731-478771
~~~

with:

~~~text
status = 200
elapsed = 66.24 s
path = /v1beta/models/gemini-2.5-pro:streamGenerateContent?alt=sse
~~~

This establishes that Gemini CLI 0.62.0 is using the Gemini-native streaming API shape, not OpenAI /v1/chat/completions.

However, the capture result must not be used as evidence that Gemini CLI successfully consumed the stream. The temporary capture proxy buffers the complete upstream response before sending response headers/body onward. Therefore a long upstream generation can produce a proxy-side 200 while Gemini CLI can still fail while waiting for or consuming the fetch. The temporary proxy is therefore unsuitable for diagnosing the precise fetch-failure root cause.

The newer 2026-10-07 13:50 Gemini CLI error report:

~~~text
/tmp/gemini-client-error-Turn.run-sendMessageStream-2026-10-07T05-50-42-587Z.json
~~~

contains only the wrapper-level error:

~~~text
exception TypeError: fetch failed sending request
~~~

with no populated errno, code, syscall, address, port, or cause fields in the extracted structure.

Therefore the current evidence supports these separate conclusions:

1. **Protocol:** Gemini CLI 0.62.0 remains a Gemini-native client in this configuration; GOOGLE_GEMINI_BASE_URL changes the Gemini API base URL and does not select OpenAI Chat Completions. The current upstream source still constructs a Google GenAI client for gateway authentication. 
2. **OpenAI-compatible native support:** There is no demonstrated built-in OpenAI-compatible provider switch in the current CLI configuration; upstream has an open feature request for this capability.
3. **Fetch failure:** The exact root cause is still open. The buffered 4010 capture is not suitable for further transport diagnosis.
4. **Next experiment:** Do not repeat broad Gemini CLI fetch testing through the buffering capture proxy. Either use a true streaming-transparent probe or test a direct Gemini-native path without 4010 while observing LiteLLM/Ollama timestamps.

This correction prevents a false attribution of the ~66 s fetch failure to Gemini CLI itself when the capture proxy can independently introduce delayed response headers.

## 22. Final state

The investigation has moved from broad performance debugging to a localized protocol/Agent-runtime problem.

### What is proven

1. **Qwen3.5:9B itself is viable for the target role.** Warm direct 16K inference is fast for tiny prompts, full-prompt prefill is measurable and approximately linear at about 37 tok/s, and native structured tool calling works.
2. **LiteLLM itself is viable.** Both OpenAI-compatible and Gemini-native text/function-calling paths work, including streaming. Gemini-native AUTO function calling works.
3. **The Gemini CLI is the major context-inflation source.** The exact captured request contains a 21.4 KB system instruction for a tiny user request.
4. **The 2050-token effective input is an Ollama 4096-runner consequence in the observed Gemini-native path.** The actual prompt was 5655 tokens and Ollama explicitly logged truncation to 2050.
5. **The Gemini-native route loses Ollama-specific runtime parameters observed here.** In particular, num_ctx=16384 was absent from the downstream request, while the OpenAI-compatible route propagated it correctly.
6. **Tool-schema translation is not the main blocker.** The Gemini-native downstream request did contain the read_file tool schema.
7. **The 80 s OpenAI-compatible control result is not evidence that 16K context is inherently slow.** It was dominated by first-time 16K runner/model initialization and 326 generated reasoning tokens.

### What remains open

~~~text
A. Gemini CLI transport
   Why does the minimal one-attempt request still fail with
   TypeError: fetch failed after about 62 s?

B. Gemini CLI structured tool execution
   Why does the CLI path produce pseudo-tool text while the manually
   constructed Gemini-native request produces a real functionCall?

C. Runtime architecture
   Can Gemini CLI be configured to use an OpenAI-compatible LiteLLM route
   with explicit Qwen/Ollama runtime parameters?

D. Production design
   If Gemini CLI remains awkward or semantically mismatched, should a thin
   Python Agent Runtime own:
       - compact task state
       - context compilation
       - explicit tool loop
       - deterministic Qwen runtime parameters
       - retry/error policy
~~~

### Current engineering direction

The next experiment should not be another generic performance benchmark.

The next decision point is:

~~~text
Can Gemini CLI → OpenAI-compatible LiteLLM → Ollama → Qwen3.5:9B
preserve the desired runtime semantics cleanly?
~~~

If yes, this may provide a simpler path to controlled local-agent execution.

If no, the evidence increasingly favors a purpose-built Python Agent Runtime with a low-entropy persistent state/context compiler.

### Reproducibility rule

Before the next experiment:

- keep ~/gemini-forensics/ captures
- do not commit raw captures containing runtime internals or secrets
- always record model identity and actual Ollama runner context with ollama ps
- distinguish cold-runner load from warm inference
- distinguish cache-hit prompt evaluation from full prompt prefill
- when comparing protocols, inspect the actual downstream request, not only the ingress configuration

The canonical evolving investigation document is:

~~~text
docs/local-qwen-coding-agent-performance-and-context-engineering-2026-10-07.md
~~~

Future sessions should update this file with new settled evidence, unresolved hypotheses, test conditions, and the next single highest-information-gain action rather than repeating already settled experiments.
