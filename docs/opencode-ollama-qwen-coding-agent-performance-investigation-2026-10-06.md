# OpenCode + Ollama + Qwen3.5 9B Coding Agent 性能调查与故障树

> 调查时间：2026-10-06  
> 调查对象：Windows 11 + WSL2 Ubuntu + Ollama 0.35.1 + OpenCode 1.18.34 + Qwen3.5 9B  
> 目标：解释 OpenCode 调用本地 Qwen3.5 9B 时为何显著变慢，并建立可复现、可证伪、可继续迭代的性能基线。
>
> 本文是本轮调查的“状态沉淀文档”，保存配置拓扑、实验场景、实测结果、故障树、request body 捕获方法、核心结论与下一阶段边界。本文不执行配置修改，只记录已经完成的实验与证据。

---

## 1. 调查背景

最初观察：

- 直接用 Ollama 调用 <code>qwen3.5:9b-opencode</code>，简单 prompt 约十几秒量级。
- OpenCode 调用同一模型时明显更慢，早期甚至出现数分钟等待、300 秒 ProviderHeaderTimeout 和 retry。
- 因此最初问题是：“为什么 OpenCode + Ollama 比直接 Ollama 慢很多？”

调查原则：

1. 逐层隔离 OpenCode 的 title、plugin、LSP、tools 等外围因素。
2. 不猜 request，直接在 Ollama 侧捕获 OpenCode 实际发送的 HTTP request body。
3. A/B 时一次只改变一个关键变量。
4. 将 OpenCode benchmark 与同一 request 的 Ollama replay 对齐。
5. 分开观察 OpenCode overhead、HTTP/网络、模型冷启动、模型 reasoning/inference。

---

# 2. 当前本地配置拓扑

## 2.1 Windows / WSL

| 项目 | 当前值 |
|---|---|
| Host | Windows 11 |
| Linux | WSL2 / Ubuntu 24.04.4 |
| CPU | Intel Core i5-11400，6C/12T |
| WSL RAM | 约 15 GiB |
| WSL Swap | 约 4 GiB |
| 项目 | <code>~/workspace/funny-tutor</code> |
| Python | <code>.venv</code> |

模型加载后，<code>ollama ps</code> 显示模型处于 loaded 状态，当前推理主要使用 CPU。高负载时 WSL 可用内存会明显下降，因此冷启动、内存压力、CPU inference 是后续优化时需要保留的变量。

## 2.2 Ollama

版本：

~~~text
ollama version is 0.35.1
~~~

主要模型：

~~~text
qwen3.5:9b
qwen3.5:9b-opencode
~~~

大致大小：

- <code>qwen3.5:9b</code>：约 6.6 GB
- <code>qwen3.5:9b-opencode</code>：约 8.7 GB
- <code>qwen3.5:9b-opencode</code> 当前 OpenCode 配置 context 为 65536

OpenCode 使用 Ollama OpenAI-compatible endpoint：

~~~text
http://127.0.0.1:11434/v1/chat/completions
~~~

## 2.3 OpenCode

版本：

~~~text
OpenCode 1.18.34
~~~

核心配置曾使用 <code>qwen3.5:9b-opencode</code> 作为 title/build/plan/bench 模型；bench 场景将 tools 关闭。

本次 clean benchmark 使用：

~~~bash
OPENCODE_CONFIG_CONTENT='{"plugin":[],"lsp":false}'
~~~

并配合：

~~~bash
--pure
--agent bench-min
~~~

以尽可能消除 plugin/LSP/tool 等外围因素。

环境中安装过：

- <code>oh-my-opencode-slim</code>
- <code>opencode-gemini-auth</code>

## 2.4 与本次调查平行的另一条 AI 链路

项目另有：

~~~text
Python
  ↓
utils/llm_client.py
  ↓
Gemini CLI
  ↓
LiteLLM :4000
  ↓
本地 Qwen 或云端 Gemini
~~~

它与本调查的：

~~~text
OpenCode → Ollama → Qwen
~~~

属于平行方案，本轮 benchmark 不将 LiteLLM/Gemini CLI 延迟混入其中。

---

# 3. 故障树：从“OpenCode 很慢”逐层收敛

## 3.1 第一层：OpenCode 自身初始化/编排

早期测试观察到：

- title enabled：约 10m4s
- 关闭 title：约 1m22.7s
- 期间出现 300s ProviderHeaderTimeoutError 和 retry

因此最初怀疑 title、plugin、LSP、tools 或内部 orchestration。

## 3.2 第二层：tools

bench，tools=false：

~~~text
~1m15.4s
~~~

bench-min，极小 prompt，tools=false：

~~~text
~56.97s
~~~

结论：即使没有实际 tools，极小任务仍然慢，因此 tools 不是 50 秒级延迟的主因。

## 3.3 第三层：plugin / LSP

clean benchmark：

~~~bash
OPENCODE_CONFIG_CONTENT='{"plugin":[],"lsp":false}' \
opencode run --pure ...
~~~

结果：

~~~text
~52.23s
~~~

这成为关键 baseline。

同时检查 <code>oh-my-opencode-slim</code> 日志发现，某些 <code>--pure</code> 场景中插件仍曾被初始化，并注册多个 agent/tools/MCP，也出现若干 v1/v2 compatibility 失败。

但核心事实是：

> 即使核心 config 明确设为 <code>plugin=[]</code>、<code>lsp=false</code>，仍然约 52 秒。

因此 plugin/LSP 不是这 52 秒的主要来源。它们可能解释早期某些分钟级异常，但不能解释 clean benchmark 的核心延迟。

---

# 4. 重大突破：从 Ollama 侧捕获 OpenCode 的真实 request

只看 OpenCode debug log 仍然无法证明 OpenCode 到底发了什么。

真正有效的方法是在 Ollama 侧开启：

~~~text
OLLAMA_DEBUG_LOG_REQUESTS=1
~~~

然后重新运行 clean benchmark。

Ollama 生成：

~~~text
/tmp/ollama-request-logs-3287921057/
~~~

以及：

~~~text
20261006T115516.941117841Z-000001_v1_chat_completions_body.json
20261006T115516.941117841Z-000001_v1_chat_completions_request.sh
~~~

这里最重要的不是“看到日志”，而是拿到了两个可实验对象：

1. <code>body.json</code>：OpenCode 真实发给 Ollama 的 request。
2. <code>request.sh</code>：可脱离 OpenCode、直接 replay 这个 request 的 shell script。

这一步把问题从：

> “猜 OpenCode 做了什么”

变成：

> “直接实验 OpenCode 实际交给 Ollama 的 request”。

这是本轮调查的方法论转折点。

---

# 5. Request body 的低熵提取结果

使用 jq 抽取关键字段，得到：

~~~json
{
  "model": "qwen3.5:9b-opencode",
  "stream": true,
  "max_tokens": 8192,
  "reasoning_effort": null,
  "messages_count": 2,
  "tools_count": 0,
  "message_roles": [
    "system",
    "user"
  ],
  "message_chars": [
    502,
    34
  ]
}
~~~

因此本次 clean request 具备以下特征：

| 参数 | 实测值 |
|---|---:|
| messages | 2 |
| system chars | 502 |
| user chars | 34 |
| tools | 0 |
| stream | true |
| max_tokens | 8192 |
| reasoning_effort | 未有效设置为 <code>"none"</code> |

由此可以排除：

- 大 prompt：总字符量很小。
- tools：数量为 0。
- 多轮状态：只有 2 messages。
- 海量上下文：本实验没有。

另一个关键事实：

> <code>reasoning_effort: null</code> 不能证明 request 中一定存在显式 null；但可以确定 OpenCode 没有有效地向 Ollama 传递 <code>reasoning_effort="none"</code>。

---

# 6. 实验 A：Replay OpenCode 原始 request

直接执行 Ollama 生成的 replay script：

~~~bash
sudo sh \
/tmp/ollama-request-logs-3287921057/20261006T115516.941117841Z-000001_v1_chat_completions_request.sh \
> /tmp/opencode_replay.out
~~~

第一次：

~~~text
~51s
~~~

第二次精确 replay：

~~~text
real    1m9.678s
user    0m0.033s
sys     0m0.013s
~~~

这直接证明：

> OpenCode 的真实 request 脱离 OpenCode 后，在 Ollama 中单独执行，仍然需要约 51–70 秒。

因此这约 50 秒不是 OpenCode UI、shell 或 framework wrapper 独有的延迟。

---

# 7. 实验 A 的协议级证据：SSE 中出现大量 reasoning

查看 <code>/tmp/opencode_replay.out</code>，可以看到大量：

~~~json
{
  "delta": {
    "content": "",
    "reasoning": "..."
  }
}
~~~

实际输出中可见类似：

~~~text
"I MUST ..."
"The system instruction mentions..."
"I am powered by ..."
~~~

说明模型在不断生成 reasoning，而不是直接返回最终 content。

因此已经有直接证据链：

~~~text
Ollama SSE
    ↓
delta.reasoning
    ↓
大量 reasoning token
    ↓
长 inference time
~~~

---

# 8. 为什么两次 Replay 都是同一个 request，却是 51s / 69.7s？

两次结果：

| Replay | 时间 |
|---|---:|
| 第一次 | ~51s |
| 第二次 | ~69.7s |

输出数据量也不同：

- 第一次约 46718 bytes
- 第二次约 86091 bytes

因此不能把 52 秒理解成固定成本。

更合理的解释是：

> Thinking ON 时，实际 reasoning/output 长度会变化，当前 CPU/WSL 条件下 latency 因此也会明显波动。

所以本阶段将 Thinking ON 的观察值记录为：

~~~text
~50–70s
~~~

而不是一个固定数字。

---

# 9. 实验 B：只改变一个变量——关闭 reasoning

从实验 A 的原始 body 派生：

~~~bash
sudo jq '.reasoning_effort = "none"' \
/tmp/ollama-request-logs-3287921057/20261006T115516.941117841Z-000001_v1_chat_completions_body.json \
> /tmp/opencode_body_no_reasoning.json
~~~

然后：

~~~bash
time sudo curl -sS -N \
  http://127.0.0.1:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ollama' \
  --data-binary @/tmp/opencode_body_no_reasoning.json \
  > /tmp/opencode_no_reasoning.out
~~~

结果：

~~~text
real    0m1.288s
user    0m0.003s
sys     0m0.004s
~~~

这里的实验控制非常重要：

> 除了增加 <code>"reasoning_effort": "none"</code>，其余 request 来自 OpenCode 原始 request。

因此这是一个高质量的 A/B 对照。

---

# 10. 实验 B 不是快速失败，而是正常成功

检查结果：

~~~text
1615 /tmp/opencode_no_reasoning.out
~~~

开头 SSE 正常返回：

~~~text
"content":"OPEN"
"content":"CODE"
"content":"_CAPTURE"
~~~

最后有：

~~~json
"completion_tokens": 5,
"total_tokens": 172
~~~

以及：

~~~text
data: [DONE]
~~~

并且：

~~~text
=== reasoning 出现次数 ===
0
~~~

所以：

> 1.288 秒是一次正常完成、无 reasoning 的 inference，不是错误、空响应或提前失败。

---

# 11. 实验 B 的模型侧 timing

Ollama 返回：

~~~json
"usage": {
  "prompt_tokens": 167,
  "prompt_tokens_details": {
    "cached_tokens": 161
  },
  "completion_tokens": 5,
  "total_tokens": 172
},
"timings": {
  "prompt_n": 167,
  "prompt_ms": 477,
  "prompt_per_second": 350.10,
  "predicted_n": 5,
  "predicted_ms": 636,
  "predicted_per_token_ms": 127.2,
  "predicted_per_second": 7.86
}
~~~

约等于：

~~~text
Prompt processing     ≈ 0.477s
Completion generation ≈ 0.636s
Inference             ≈ 1.113s
Command total        ≈ 1.288s
~~~

因此当前获得了一个很干净的：

> warm model + reasoning OFF + tiny prompt

基线。

---

# 12. 冷启动与 reasoning 必须分开

本轮还做过：

~~~text
/v1 stream=true + reasoning_effort=none
TTFB  ≈ 13.08s
TOTAL ≈ 14.00s
~~~

当时大部分时间来自模型加载。

而实验 B：

~~~text
warm model
+
reasoning_effort=none
+
tiny prompt
≈ 1.288s
~~~

所以当前至少要区分三个状态：

| 状态 | 典型观察 |
|---|---:|
| Model cold start | 约十几秒量级 |
| Thinking ON | 约 50–70 秒量级 |
| Warm + Thinking OFF | 约 1.3 秒量级 |

这三个数字不能混为一个“本地 Qwen 速度”。

---

# 13. 关键性能矩阵

| 场景 | 路径 | Thinking | tools | plugin/LSP | 时间 | 结论 |
|---|---|---:|---:|---:|---:|---|
| Title enabled | OpenCode | 默认 | 未完全隔离 | 未完全隔离 | ~10m4s | 早期异常放大 |
| Title disabled | OpenCode | 默认 | 低/0 | 常规 | ~1m22.7s | 外围逻辑会放大异常 |
| Bench | OpenCode | 默认 | 0 | 常规 | ~1m15.4s | tools 不是主因 |
| Bench-min | OpenCode | 默认 | 0 | 常规 | ~56.97s | 小 prompt 仍慢 |
| Clean / pure | OpenCode | 默认 | 0 | plugin=[] / lsp=false | **~52.23s** | 52s 不是外围 framework 主因 |
| Replay A | Ollama，OpenCode原request | **ON** | 0 | N/A | **~51s** | 可脱离 OpenCode 复现 |
| Replay A #2 | Ollama，OpenCode原request | **ON** | 0 | N/A | **~69.7s** | reasoning/output 长度导致波动 |
| Replay B | 同 request，仅 <code>reasoning_effort=none</code> | **OFF** | 0 | N/A | **1.288s** | **决定性证据** |

---

# 14. 当前故障树

~~~text
OpenCode + Ollama + Qwen3.5 9B “很慢”
│
├── 1. OpenCode 自身 / 初始化
│   ├── title
│   ├── plugin
│   ├── LSP
│   └── tools
│
│   clean:
│   plugin=[] + lsp=false + tools=0
│   → 仍 ≈52s
│   → 不是 52s 主因
│
├── 2. Prompt / context 太大
│   └── system=502 chars
│       user=34 chars
│       messages=2
│       tools=0
│       → 不是
│
├── 3. Ollama HTTP / curl
│   └── replay 同一 request
│       → 仍 ≈51–70s
│       → curl/network 不是主因
│
└── 4. Qwen inference
    │
    ├── reasoning_effort 未有效关闭
    │      ↓
    │   SSE 出现 delta.reasoning
    │      ↓
    │   ≈51–70s
    │
    └── reasoning_effort="none"
           ↓
        reasoning=0
           ↓
        正常完成
           ↓
        ≈1.288s
           ★ 当前最强根因
~~~

---

# 15. 核心结论

## 15.1 OpenCode 本身不是 50 秒延迟的主要来源

clean benchmark：

~~~text
OpenCode ≈52.2s
~~~

同一 request 脱离 OpenCode、直接 replay 到 Ollama：

~~~text
≈51–70s
~~~

因此：

> 约 50 秒主要发生在模型 inference，而不是 OpenCode wrapper/UI 本身。

---

## 15.2 Thinking/reasoning 是当前最强的性能决定变量

同一 request：

~~~text
reasoning 未关闭
→ ~51–70s
→ 大量 delta.reasoning
~~~

仅改：

~~~json
"reasoning_effort": "none"
~~~

变成：

~~~text
→ 1.288s
→ 0 reasoning
→ 正常答案
~~~

倍率：

~~~text
~51s / 1.288s ≈ 39.6x
~69.7s / 1.288s ≈ 54.1x
~~~

这些倍率只代表本次 tiny-prompt benchmark，不应外推到所有 coding task。

---

## 15.3 <code>--variant none</code> 没有被证明等价于 Ollama <code>reasoning_effort="none"</code>

OpenCode 测试使用过：

~~~bash
--variant none
~~~

但 Ollama capture 到的 request 中：

~~~json
"reasoning_effort": null
~~~

而不是：

~~~json
"reasoning_effort": "none"
~~~

所以现在真正值得研究的问题已经收敛为：

> OpenCode 1.18.34 的 <code>--variant none</code> 是如何映射到 AI SDK / OpenAI-compatible request 的？为什么最终没有成为 Ollama 所需的 <code>reasoning_effort="none"</code>？

---

## 15.4 之前直接配置 <code>reasoningEffort: "none"</code> 的尝试不能直接视为正确方案

此前相关配置尝试出现：

~~~text
约 6m8s
300s ProviderHeaderTimeout
retry
~~~

因此当前不把这个方案标记为已验证解决方案，而是暂时冻结，待参数映射链路明确后再处理。

---

## 15.5 当前硬件上的本地 Qwen 并非“天然慢”

实验 B：

~~~text
warm
+
reasoning off
+
167 prompt tokens
+
5 completion tokens
→ 1.288s
~~~

说明当前硬件上，至少在：

> warm + tiny prompt + reasoning off

条件下，本地 Qwen3.5 9B 能达到秒级响应。

因此后续重点应该转向真正的 coding-agent 优化，而不是简单得出“本地 Ollama 不适合 coding agent”。

---

# 16. Ollama request body 捕获技巧

这是本轮最值得长期保留的工程技巧。

## 16.1 开启 request logging

设置：

~~~text
OLLAMA_DEBUG_LOG_REQUESTS=1
~~~

让 Ollama 保存 inference request body 和 replay command。

## 16.2 找到 body 和 replay script

典型形式：

~~~text
/tmp/ollama-request-logs-*/<timestamp>_v1_chat_completions_body.json
/tmp/ollama-request-logs-*/<timestamp>_v1_chat_completions_request.sh
~~~

## 16.3 用 jq 做低熵分析

推荐只提取：

~~~bash
sudo jq '{
  model,
  stream,
  max_tokens,
  reasoning_effort,
  messages_count: (.messages | length),
  tools_count: (.tools // [] | length),
  message_roles: [.messages[].role],
  message_chars: [.messages[].content | length]
}' ..._body.json
~~~

这种方法保留真正影响根因判断的字段，而不是把整个 request body 充满上下文。

## 16.4 replay script 是最有价值的实验工具

直接：

~~~bash
sudo sh /tmp/..._request.sh
~~~

即可把：

~~~text
OpenCode
~~~

从链路中剥离，只测试：

~~~text
request → Ollama → model
~~~

因此它特别适合排查：

- Agent framework；
- OpenAI-compatible adapter；
- middleware；
- reasoning 参数；
- tools 注入；
- prompt/context 膨胀。

## 16.5 为什么经常需要 sudo

request log 可能由服务进程以 root 权限生成并采用严格权限，因此：

~~~bash
sudo jq ...
sudo sh ...
~~~

是正常的读取/Replay 方法。

---

# 17. 低熵上下文工程：本轮调查形成的方法论

推荐固定成：

~~~text
Observation
    ↓
Hypothesis
    ↓
Isolation
    ↓
Capture actual request
    ↓
Replay outside framework
    ↓
A/B with one variable
    ↓
Observe model-side evidence
    ↓
Update fault tree
    ↓
Freeze conclusion
~~~

而不是：

~~~text
OpenCode 慢
↓
不断改配置
↓
重复运行
↓
结果变化
↓
凭感觉猜原因
~~~

对于：

~~~text
Agent framework
+ plugin
+ LSP
+ tools
+ middleware
+ OpenAI-compatible adapter
+ inference server
+ reasoning model
~~~

直接捕获最终 request，通常比只看 framework 高层日志更能快速降低问题熵。

---

# 18. 当前 Investigation State

## 已确认

- [x] OpenCode 1.18.34 可使用 Ollama <code>/v1</code>
- [x] clean benchmark 可大幅剥离 plugin/LSP/tools
- [x] clean benchmark 仍约 52 秒
- [x] 已从 Ollama 成功捕获 OpenCode 实际 request body
- [x] request 很小：2 messages、0 tools
- [x] 原始 request 可在 OpenCode 之外 replay，约 51–70 秒
- [x] replay SSE 明确出现大量 <code>delta.reasoning</code>
- [x] 同一 request 仅增加 <code>reasoning_effort="none"</code> 后约 1.288 秒
- [x] 无 reasoning 时正常返回，reasoning 次数为 0
- [x] 当前最强根因：Qwen reasoning/thinking 没有被 OpenCode 有效关闭

## 尚未确认

- [ ] OpenCode 1.18.34 <code>--variant none</code> 的真实参数映射
- [ ] AI SDK OpenAI-compatible provider 是否吞掉/转换 reasoning 参数
- [ ] 为什么直接尝试 <code>reasoningEffort: "none"</code> 会出现 300 秒 timeout/retry
- [ ] 如何在不破坏 tool calling / agent loop 的情况下安全关闭或分级控制 reasoning
- [ ] 真实 coding task 的端到端速度：多轮、tool-call、长上下文
- [ ] context 32768 vs 65536 对当前 WSL 资源的影响
- [ ] CPU/RAM/swap 与长期 warm-model coding session 的最佳平衡

---

# 19. 下一阶段问题定义

本阶段到此暂停，不再继续泛化调查“OpenCode 为什么慢”。

下一阶段的真正问题是：

> **在当前硬件约束下，如何最大化本地 Ollama + Qwen3.5 9B 的 coding-agent 能力，并把有限 CPU/RAM 转化为尽可能高的有效 agent throughput。**

建议按以下顺序：

~~~text
1. 正确控制 reasoning
2. 保证 tool calling 稳定
3. 控制上下文增长
4. 控制 agent loop
5. warm model / cold start 策略
6. context / output token budget
7. 真实 coding-task benchmark
~~~

---

# 20. 一句话状态总结

> 截至 2026-10-06，本次调查已经把“OpenCode + Ollama + Qwen3.5 9B 很慢”从一个宽泛的 framework 性能问题，收敛成一个具体的协议/模型调用问题：OpenCode 实际发送给 Ollama 的 request 很小、无 tools；原始 request 在 Ollama 中独立 replay 仍耗时约 51–70 秒，并产生大量 reasoning；而同一 request 仅增加 <code>reasoning_effort="none"</code> 后即可在 warm model 状态下约 1.288 秒正常完成。下一阶段应集中研究 OpenCode → AI SDK → Ollama 的 reasoning 参数映射，以及如何在现有硬件条件下构建高效的本地 Qwen coding-agent 工作模式。

---

## 参考资料

- Ollama OpenAI compatibility / reasoning：
  https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx
- Ollama request logging：
  https://github.com/ollama/ollama/blob/main/server/inference_request_log.go
- Ollama environment configuration：
  https://github.com/ollama/ollama/blob/main/envconfig/config.go
- OpenCode × Ollama integration：
  https://github.com/ollama/ollama/blob/main/docs/integrations/opencode.mdx
