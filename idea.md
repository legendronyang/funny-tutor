# Idea: Funny Tutor 题库 — JSON Canonical + Obsidian-Native（高二电磁学实战版）

## Problem Statement
如何在高二上学期的紧张节奏下，把「电磁感应、交流电等重图文、重公式的真题」变成一套按知识点查漏补缺的题库，并通过 Obsidian 提供无需检索、开箱即阅的“每日 3 分钟 Funny 微学习卡片”，同时避免陷入高成本的 Web 平台开发？

## Recommended Direction
核心思路：以统一 JSON 作为题库真相源（Canonical Model），用 Python 脚本串联 LLM 与“每日任务看板”，Obsidian 作为首选呈现端，不让 AI 当解题引擎，而只做“语言与记忆的放大器”。

1. 统一、面向多前端的 JSON Schema（兼容图文与 LaTeX）
   - 元数据：id, year, paper, subject=physics, index, score, question_type。
   - 内容层：question_raw, options, answer, analysis_official，外加 images_paths[]（电路图、波形图等本地资源引用），要求原始 LaTeX 和图片信息在 JSON 中完整可还原。
   - 知识结构层：knowledge_main, knowledge_tree_path（如 ["磁与电磁感应","电磁感应","感应电动势与楞次定律"]）, exam_tags, difficulty。
   - 知识点对象：knowledge_points[]（id, name, summary_plain, prerequisites, typical_pitfalls），为“按知识点查漏补缺”和后续统计打基础。
   - Funny 钩子层：memory_aids[], funny_quick_tip, common_misconceptions[]，只描述语言和记忆，不重复解析推导。
   JSON 不绑定 Obsidian，本质上是一个可被任意前端消费的题库内核。

2. Python + LLM 的“双轨生成”：题卡片生成 + 每日看板生成
   - 内容生成轨：脚本读取 JSON 调用 LLM，强制约束：
     - 不改动公式和关键物理量名称（LaTeX 原样拷贝）。
     - 以 analysis_official 和 knowledge_points 为依据，只在解释性文字层做“大白话 + Funny 化”重写。
     - 产出 1 至 3 条记忆钩子（顺口溜、类比、形象比喻）和典型易错点列表，写入 Obsidian 用的 .md 卡片。
   - 交互生成轨：每次脚本运行时同步重建首页文件 00_今日电磁学吐槽.md，从题库中按简单规则（随机或基于“新题 + 复习题”的权重）抽取三到五题，生成带双链的“今日任务清单”，尽量把“要学什么”这一步做到零思考成本。

3. Obsidian 作为高频“电磁学错题本 + 知识图谱”前端
   - 展现层：每题一页，结构固定：
     - 标题含年份、卷别和简短知识点，如 [2018 全国一卷 第12题] 感应电动势与楞次定律。
     - 标签如 #高中物理/电磁学 #真题/选择题，双链指向章节总览，如 [[电磁感应]]、[[交流电]]。
     - 使用 callout 呈现情绪化内容：> [!tip] Funny Tutor 展示大白话和记忆钩子，> [!warning] 翻车点 展示典型误区。
   - 录入层：为降低早期录题成本，日常只需拍照丢进 Obsidian Inbox 文件夹，周期性用 OCR（Mathpix 等）和简易脚本将图片转成 question_raw + images_paths 形式的 JSON 再进入批处理管线，人手录入只承担格式校对而不是全文重敲。

## Key Assumptions to Validate
- [ ] 录题成本可控：在 OCR 辅助下，包含 LaTeX 和电路图的电磁学题目录入到 JSON 的综合时间成本，可接受为“每题几分钟级别”，不会让维护题库本身成为新的负担。
- [ ] 物理概念不被 Funny 化篡改：经过精心设计的 Prompt 后，LLM 在生成大白话和吐槽时能保持对关键物理概念（如“磁通量变化率”“有效值与峰值”“相位关系”）的一致性与严谨性，错误率在可人工审核范围内。
- [ ] 每日看板确实降低启动门槛：自动生成的 00_今日电磁学吐槽.md 让高二学生可以“一键点开就知道今天看哪几题”，显著弱化在 Obsidian 里自己乱翻文件夹的心理摩擦。
- [ ] 情绪记忆对电磁学有效：对比传统解析，带顺口溜、类比的 Funny 区块能在三天后显著提升对“题型 + 知识点组合”的回忆率，而不过分影响对公式本身的严肃记忆。
- [ ] Obsidian 接受度足够高：目标用户愿意在现有学习工具之外额外安装并使用 Obsidian，把其视作“电磁学专属外挂”而不是负担。

## MVP Scope

| 模块 | 核心功能要求 | 交付物 |
| :--- | :--- | :--- |
| 电磁学图文 JSON 库 | 根据至少二十道高二电磁学真题，构建包含 LaTeX 公式和本地图片引用（assets/）的标准 JSON，字段覆盖元数据、知识结构、Funny 钩子。 | questions_em.json 与 /assets 目录 |
| 防幻觉 Funny Prompt | 设计并验证 System Prompt 与少量 Few-shot 示例，硬性要求“物理变量和公式原样保留，只在解释与比喻处 Funny”，并输出清晰的使用说明。 | funny_tutor_prompt_em.txt |
| 双轨生成 Python 脚本 | 完成一个脚本：其一把 JSON 转换为带 callout 的 Obsidian 笔记，其二生成或更新 00_今日电磁学吐槽.md 首页，内含若干条当日任务的题目双链。 | generate_em_vault.py |
| Obsidian 最小 Vault | 搭建独立 Vault：包含基础文件夹结构（按知识树划分）、二十篇示例笔记、00_今日电磁学吐槽.md 首页、图床文件夹，以及基本主题配置。 | FunnyTutor_EM_Vault/ 仓库 |

## Not Doing (and Why)
- 不开发所见即所得的录题前端：录带 LaTeX 的 JSON 确实辛苦，但在 MVP 阶段更重要的是验证“输出端的阅读与记忆价值”，前二十题可以接受半手工录入，录题工具可留在第二阶段。
- 不引入复杂插件依赖（如 Dataview 驱动 UI）：尽量让生成的 Markdown 在“纯文本 + Obsidian 原生特性”下即可良好工作，减少环境差异带来的调试成本。
- 不让 AI 主动推导复杂计算过程：电磁感应和交流电中的定量推导仍依赖权威解析或人工编写，LLM 只负责翻译与重构语言，以避免在推导细节上产生不可控幻觉。
- 不一次性扩展到全学科、多端同步：MVP 只服务高二电磁学，默认单机或家庭级 Vault；跨设备同步交由 Obsidian 自身或网盘解决，后续如果验证价值再考虑 Web 端或多用户协作。