# tasks/plan.md

# Implementation Plan: Funny Tutor - EM Vault Generator

## Overview
本项目旨在构建一个轻量级、可重复运行且增量友好的 Python 批处理管道。该管道以 JSON 格式的电磁学题库为真相源，调用大模型（Gemini）生成 Funny Tutor 风格的解析与记忆钩子，最终输出为 Obsidian 原生的 Markdown 题卡库及每日任务看板。核心在于解耦数据层、大模型处理层与呈现层，并解决 JSON 解析的容错问题以及 Obsidian 沙盒隔离导致的图片加载问题。

## Architecture Decisions
- 垂直切分与单向依赖：以底层数据定义（Pydantic Schema）为基石，纯函数层与外部依赖层互不干扰，最后由主控脚本统一调度。
- 增量生成策略：基于文件系统的存在性检测进行增量判断，跳过已存在题卡的 LLM 请求。
- 资产沙盒同步：主控脚本在运行时负责将源数据的 data/assets/ 目录全量复制或同步至 Vault 的资产目录内（vault/FunnyTutor_EM_Vault/assets/）。
- 防爆破 JSON 解析：LLM 客户端必须包含剥离代码块外壳的清洗逻辑。

## Task List

### Phase 1: Foundation & API
- [ ] Task 1: 项目骨架初始化与数据模型 Schema
- [ ] Task 2: 封装大模型客户端与 JSON 清洗逻辑

### Checkpoint: Foundation
- [ ] Pydantic 模型测试通过，能正确拦截非法 JSON。
- [ ] LLM 客户端 Mock 测试通过，能成功剥离代码块外壳并解析 JSON。

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

## Risks and Mitigations
| Risk | Impact | Mitigation |
| | | |
| 大模型返回包裹了代码块符号的 JSON 导致解析崩溃 | High | 在 llm_client 中使用正则提取，测试用例强制覆盖纯文本与带外壳文本两种情况。 |
| Obsidian 沙盒策略导致外部图片显示为死链 | High | 主脚本执行 shutil.copytree 强制将 data/assets/ 同步到 Vault 内部的 assets/，渲染器使用相对路径。 |
| 误操作重新生成全部题库导致 Token 爆炸 | Medium | 默认开启增量判定，只有检测到文件不存在或显式传入 force 标志时才发起网络请求。 |

## Open Questions
- 随着题量增加，简单的随机抽题是否会导致新题曝光率不足？（MVP 阶段暂不处理，后续可引入按日期权重的抽题策略）
