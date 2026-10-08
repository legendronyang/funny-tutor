# tasks/plan.md

# Implementation Plan: Funny Tutor - EM Vault Generator

## Overview
本项目旨在构建一个轻量级、可重复运行且增量友好的 Python 批处理管道。该管道以 JSON 格式的电磁学题库为真相源，通过 LiteLLM 调用可切换的大模型（开发阶段默认本地 Ollama/Qwen3.5:9b-opencode，后续可用 Gemini、ChatGPT 等云端模型独立复核）生成 Funny Tutor 风格的解析与记忆钩子，最终输出为 Obsidian 原生的 Markdown 题卡库及每日任务看板。核心在于解耦数据层、大模型处理层与呈现层，并解决 JSON 解析的容错问题以及 Obsidian 沙盒隔离导致的图片加载问题。

## Architecture Decisions
- 垂直切分与单向依赖：以底层数据定义（Pydantic Schema）为基石，纯函数层与外部依赖层互不干扰，最后由主控脚本统一调度。
- LLM provider abstraction：业务代码只依赖统一的 LLM Client；底层通过 LiteLLM 路由到 Ollama/Qwen、Gemini、ChatGPT 等模型，切换 provider 不修改业务逻辑。
- Canonical question bank：`data/questions_em.json` 是开发阶段的测试素材，不定义正式题库 Schema。正式题库由 `EMQuestion` 定义；来源可以是人工录入、OCR 或其他外部系统，这些来源不属于当前项目边界。
- Independent verification：题库中已有答案/解析时，模型必须独立求解后再与已有内容比较；不得把 provided answer 当作模型推理依据。空字段进入 generation，已有字段进入 verification。验证结果应保留来源模型、时间、结论和必要的差异信息。
- 增量生成策略：基于文件系统的存在性检测进行增量判断，跳过已存在题卡的 LLM 请求。
- LLM 输出边界：Generate 模式只允许 FunnyTutorPayload 的三个字段；validated payload 之外的任何字段不得进入 Markdown renderer。
- 资产沙盒同步：主控脚本在运行时负责将源数据的 data/assets/ 目录全量复制或同步至 Vault 的资产目录内（vault/FunnyTutor_EM_Vault/assets/）。
- 防爆破 JSON 解析：LLM 客户端必须包含剥离代码块外壳的清洗逻辑。
- 严格 Generate 输出契约：JSON extraction 之后必须通过 FunnyTutorPayload Pydantic schema；额外字段、缺字段或错误嵌套类型一律拒绝。
- Native structured output：当前 Ollama `ollama_chat` Generate 请求同时传递 FunnyTutorPayload 的 JSON Schema 与 temperature=0.0，减少 Qwen 在 JSON 外壳和字段结构上的随机偏离；本地 Pydantic 校验仍保留为最后一道边界。

## Task List

### Phase 1: Foundation & API
- [x] Task 1: 项目骨架初始化与数据模型 Schema
- [x] Task 2: LiteLLM 大模型客户端、结构化 JSON 清洗与 Generate/Verify 契约

### Checkpoint: Foundation
- [x] Pydantic 模型测试通过，能正确拦截非法 JSON。
- [x] LLM 客户端 Mock 测试通过，能成功剥离代码块外壳并解析 JSON。
- [x] Generate/Verify 判定测试通过：字段为空时生成，已有字段时独立核实。

### Phase 2: Pure Functions
- [ ] Task 3: Markdown 卡片渲染器
- [ ] Task 4: 每日看板随机抽题逻辑

### Checkpoint: Pure Functions
- [ ] 渲染器输出包含正确的 Callout 和 LaTeX 原样保留。
- [ ] 抽题逻辑能准确返回指定数量的不重复题目 ID。

### Phase 3: Pipeline Integration
- [ ] Task 5: 主管道脚本、资产同步与 IO 写出
- [x] Task 6: 旧题库导入适配器与 Canonical Schema 转换
- [ ] Task 7: LLM Generate 输出契约强化与真实 Smoke Test

### Task 7: LLM Generate 输出契约强化

- 真实 Smoke Test 暴露了合法 JSON 与业务 payload 不一致的问题。
- Generate 使用 FunnyTutorPayload 严格校验，禁止额外 canonical 字段和错误嵌套类型。
- generate_vault.py 在持久化前再次校验并采用 payload 字段白名单。
- Prompt 与 Spec 同步定义三个允许输出键。
- 本任务的最终验收必须包含一次真实 Qwen 单题 Smoke Test；通过后才允许进入 10 题全量生成。

### Checkpoint: Complete
- [ ] 增量生成逻辑生效，二次运行无多余 LLM 请求。
- [ ] 生成的 Vault 在 Obsidian 中图片加载与公式渲染正常。
- [ ] 测试用例与代码静态检查全部通过。

## LLM Verification Contract

- `generation`：目标字段没有可信值时，由当前模型生成。
- `verification`：已有答案/解析等可信值时，模型独立求解，不把 provided value 注入为结论，再与其比较并记录 verdict。
- 模型路由由配置决定；开发阶段默认 `ollama_chat/qwen3.5:9b-opencode`；Ollama thinking policy 由 LLM Client 根据 Generate/Verify 模式映射，后续可切换云端模型进行独立复核。
- 正式题库应能保存 canonical content 与多模型 verification evidence，而不是用某一个模型的输出覆盖真相源。

## Risks and Mitigations
| Risk | Impact | Mitigation |
| | | |
| 大模型返回包裹了代码块符号的 JSON 导致解析崩溃 | High | 在 llm_client 中使用正则提取，测试用例强制覆盖纯文本与带外壳文本两种情况。 |
| 大模型返回合法 JSON 但业务结构错误或夹带 canonical 字段 | High | Generate 使用 FunnyTutorPayload(extra="forbid") 严格校验；pipeline 在写卡前再校验一次，并采用字段白名单 merge。 |
| Obsidian 沙盒策略导致外部图片显示为死链 | High | 主脚本执行 shutil.copytree 强制将 data/assets/ 同步到 Vault 内部的 assets/，渲染器使用相对路径。 |
| 误操作重新生成全部题库导致 Token 爆炸 | Medium | 默认开启增量判定，只有检测到文件不存在或显式传入 force 标志时才发起网络请求。 |

## Open Questions
- 随着题量增加，简单的随机抽题是否会导致新题曝光率不足？（MVP 阶段暂不处理，后续可引入按日期权重的抽题策略）

## Task 6 / Task 7 Closure Evidence

- Task 6 本地验证：10 条旧题库记录成功转换为 Canonical JSON；Dry-run total=10、failed=0；ruff check 通过；pytest 55 tests 全部通过；原始 data/questions_em.json 无 diff。
- Task 7 曾进行真实单题 Smoke Test，Qwen 返回合法 JSON 但缺少 funny_explanation、将 memory_aids/common_misconceptions 生成为对象数组，并夹带 knowledge_main/knowledge_tree_path/knowledge_points；该结果推动严格 Generate payload schema 与 Prompt 强化，当前 Task 7 的代码验收仍需用户重新运行真实 Smoke Test。

## Task 2 Closure Evidence

- Runtime configuration: `qwen3.5:9b-opencode`, `think_generate=false`, `think_verify=true`, `timeout=1800s`.
- Formal A/B integration: `test_logs/test_verify_think_on_ab.log` completed 2/2 PASS. A took 840.821s; B took 1221.123s; total elapsed 2061.952s (about 34m21.95s).
- Exploratory `think=false` direct-Ollama logs remain in `test_logs/` as diagnostic evidence and are not the formal Verify acceptance path.
