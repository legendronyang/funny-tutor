# tasks/plan.md

# Implementation Plan: Funny Tutor - EM Vault Generator

## Overview
本项目旨在构建一个轻量级、可重复运行且增量友好的 Python 批处理管道。该管道以 JSON 格式的电磁学题库为真相源，通过 LiteLLM 调用可切换的大模型（开发阶段默认本地 Ollama/Qwen3.5:9b，后续可用 Gemini、ChatGPT 等云端模型独立复核）生成 Funny Tutor 风格的解析与记忆钩子，最终输出为 Obsidian 原生的 Markdown 题卡库及每日任务看板。核心在于解耦数据层、大模型处理层与呈现层，并解决 JSON 解析的容错问题以及 Obsidian 沙盒隔离导致的图片加载问题。

## Architecture Decisions
- 垂直切分与单向依赖：以底层数据定义（Pydantic Schema）为基石，纯函数层与外部依赖层互不干扰，最后由主控脚本统一调度。
- LLM provider abstraction：业务代码只依赖统一的 LLM Client；底层通过 LiteLLM 路由到 Ollama/Qwen、Gemini、ChatGPT 等模型，切换 provider 不修改业务逻辑。
- Canonical question bank：`data/questions_em.json` 是开发阶段的测试素材，不定义正式题库 Schema。正式题库由 `EMQuestion` 定义；来源可以是人工录入、OCR 或其他外部系统，这些来源不属于当前项目边界。
- Independent verification：题库中已有答案/解析时，模型必须独立求解后再与已有内容比较；不得把 provided answer 当作模型推理依据。空字段进入 generation，已有字段进入 verification。验证结果应保留来源模型、时间、结论和必要的差异信息。
- 增量生成策略：基于文件系统的存在性检测进行增量判断，跳过已存在题卡的 LLM 请求。
- 资产沙盒同步：主控脚本在运行时负责将源数据的 data/assets/ 目录全量复制或同步至 Vault 的资产目录内（vault/FunnyTutor_EM_Vault/assets/）。
- 防爆破 JSON 解析：LLM 客户端必须包含剥离代码块外壳的清洗逻辑。

## Task List

### Phase 1: Foundation & API
- [x] Task 1: 项目骨架初始化与数据模型 Schema
- [ ] Task 2: LiteLLM 大模型客户端、结构化 JSON 清洗与 Generate/Verify 契约

### Checkpoint: Foundation
- [ ] Pydantic 模型测试通过，能正确拦截非法 JSON。
- [ ] LLM 客户端 Mock 测试通过，能成功剥离代码块外壳并解析 JSON。
- [ ] Generate/Verify 判定测试通过：字段为空时生成，已有字段时独立核实。

### Phase 2: Pure Functions
- [ ] Task 3: Markdown 卡片渲染器
- [ ] Task 4: 每日看板随机抽题逻辑

### Checkpoint: Pure Functions
- [ ] 渲染器输出包含正确的 Callout 和 LaTeX 原样保留。
- [ ] 抽题逻辑能准确返回指定数量的不重复题目 ID。

### Phase 3: Pipeline Integration
- [ ] Task 5: 主管道脚本、资产同步与 IO 写出

### Checkpoint: Complete
- [ ] 增量生成逻辑生效，二次运行无多余 LLM 请求。
- [ ] 生成的 Vault 在 Obsidian 中图片加载与公式渲染正常。
- [ ] 测试用例与代码静态检查全部通过。

## LLM Verification Contract

- `generation`：目标字段没有可信值时，由当前模型生成。
- `verification`：已有答案/解析等可信值时，模型独立求解，不把 provided value 注入为结论，再与其比较并记录 verdict。
- 模型路由由配置决定；开发阶段默认 `ollama_chat/qwen3.5:9b`；Ollama thinking policy 由 LLM Client 根据 Generate/Verify 模式映射，后续可切换云端模型进行独立复核。
- 正式题库应能保存 canonical content 与多模型 verification evidence，而不是用某一个模型的输出覆盖真相源。

## Risks and Mitigations
| Risk | Impact | Mitigation |
| | | |
| 大模型返回包裹了代码块符号的 JSON 导致解析崩溃 | High | 在 llm_client 中使用正则提取，测试用例强制覆盖纯文本与带外壳文本两种情况。 |
| Obsidian 沙盒策略导致外部图片显示为死链 | High | 主脚本执行 shutil.copytree 强制将 data/assets/ 同步到 Vault 内部的 assets/，渲染器使用相对路径。 |
| 误操作重新生成全部题库导致 Token 爆炸 | Medium | 默认开启增量判定，只有检测到文件不存在或显式传入 force 标志时才发起网络请求。 |

## Open Questions
- 随着题量增加，简单的随机抽题是否会导致新题曝光率不足？（MVP 阶段暂不处理，后续可引入按日期权重的抽题策略）
