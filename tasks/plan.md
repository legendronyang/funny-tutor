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
- [x] Task 3: Markdown 卡片渲染器（代码与单元测试已实现；Obsidian 手工渲染验收待做）
- [x] Task 4: 每日看板随机抽题逻辑（代码与单元测试已实现）

### Checkpoint: Pure Functions
- [ ] 渲染器输出包含正确的 Callout 和 LaTeX 原样保留。
- [ ] 抽题逻辑能准确返回指定数量的不重复题目 ID。

### Phase 3: Pipeline Integration
- [x] Task 5: 主管道脚本、资产同步与 IO 写出（实现已完成；本次增加 force 失败时隔离旧卡的回归保护，需本地测试确认）
- [x] Task 6: 旧题库导入适配器与 Canonical Schema 转换
- [x] Task 7: LLM Generate 输出契约（结构化实现完成；真实模型内容质量验收未通过，详见 tech-debt.md）

### Task 7: LLM Generate 输出契约强化

- 真实 Smoke Test 暴露了合法 JSON 与业务 payload 不一致的问题。
- Generate 使用 FunnyTutorPayload 严格校验，禁止额外 canonical 字段和错误嵌套类型。
- generate_vault.py 在持久化前再次校验并采用 payload 字段白名单。
- Prompt 与 Spec 同步定义三个允许输出键。
- 本任务的最终验收必须包含一次真实 Qwen 单题 Smoke Test；通过后才允许进入 10 题全量生成。
- 首卡内容 Quality Gate 独立于结构化输出 Gate：检查矢量方向/大小、不臆断题设、单位与幂次、数量级、以及本题针对性的易错点。该检查当前是人工内容验收，不声称 Pydantic 能证明物理正确性。
- 对于求电荷量大小的题目，质量 Gate 还要求在正文中始终使用绝对值公式（如 `|q|E=mg`、`|q|=mg/E`），并解释低于临界电荷量时电场力不足以平衡重力。方向不能凭空假定，但可以从题目明确支持的平衡条件推导。
- 来源保护与生成准确性必须分层：canonical 原题/答案/官方解析严格只读，但 Funny Tutor 可以在新生成文本中独立给出更严谨的等价公式，不应因来源解析出现带符号表达就照抄到求电荷量大小的解释中。首题还要求明确展示 `r=1 mm=10^-3 m` 及 `r^3=(10^-3 m)^3=10^-9 m^3`。
- 公式一致性必须逐段覆盖 `funny_explanation`、`memory_aids` 和 `common_misconceptions`；JSON 字符串中的 LaTeX 反斜杠须正确转义，最终 Markdown 不得出现由 `\r` 等转义造成的断裂公式。数量级解释需准确区分：将 `1 mm` 直接当作 `1 m` 导致 `10^9` 倍体积/质量/临界电荷误差；将 `r^3` 错写为 `10^-3 m^3` 而不是 `10^-9 m^3` 则相差 `10^6` 倍。

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
- Task 7 曾进行真实单题 Smoke Test，Qwen 返回合法 JSON 但缺少 funny_explanation、将 memory_aids/common_misconceptions 生成为对象数组，并夹带 knowledge_main/knowledge_tree_path/knowledge_points；随后又出现同一链路的非 JSON 响应，说明仅依赖 Prompt 不足。当前实现已升级为 Prompt + Ollama JSON Schema structured output + Pydantic validation，并将 Generate temperature 固定为 0.0；仍需用户重新运行真实 Smoke Test 验收。
- 最新单题端到端 Smoke Test 已结构性通过：`generated=1, skipped=0, failed=0`，运行约 1m45s，Markdown 中存在 Funny Tutor 与翻车点 Callout；但内容 Gate 未通过，因为解释将电场力未经条件说明地称为“向上推力”，易错点也未优先覆盖毫米到米的换算与半径三次方。Prompt 已在 commit `3a81a7452f226ecf9d26bebcb142d8453e8588b4` 加入方向/大小、禁止补条件、单位/数量级和题目针对性约束；下一步由用户用同一题复测，质量 Gate 尚未判定通过。
- 后续单题 Smoke Test（约 1m15.7s）已改善方向推理和单位/幂次提醒，但仍在正文中混用 `q=mg/E` 与 `|q|E=mg`，且未充分解释最小阈值的因果条件。Prompt 已在 commit `cdd5dca7b0e5d519d48e2a14dd40f4941d0c3e0a` 强化：求电荷量大小时公式统一使用绝对值；若最小值对应临界平衡，应说明低于阈值时电场力为何不足以抵消重力。内容 Quality Gate 仍待用户对同一题复测。
- 新一轮单题 Smoke Test（约 1m55.7s）已解释低于阈值时电场力不足，但生成正文仍使用 `mg=Eq`，只在后面的记忆辅助单独写 `|q|=mg/E`，单位换算也未明确写出 `r=1 mm=10^-3 m` 与立方结果。Prompt 进一步修改为 commit `8ed928036616c271652e75418c94331687a686cb`：澄清 canonical 来源只读不限制新生成内容写出严谨等价公式，并要求首题显式展示单位/立方换算。质量 Gate 仍待复测。
- 最新单题 Smoke Test（约 2m51.5s，commit `cab0509`）已显式写出单位/立方结果并解释临界电荷量，但正文仍出现 `mg=Eq`、`Eq=10^4×q`，与绝对值写法不一致；Funny Tutor 的密度公式显示为断裂的 `$ ... ho# tasks/plan.md

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
- 首卡内容 Quality Gate 独立于结构化输出 Gate：检查矢量方向/大小、不臆断题设、单位与幂次、数量级、以及本题针对性的易错点。该检查当前是人工内容验收，不声称 Pydantic 能证明物理正确性。
- 对于求电荷量大小的题目，质量 Gate 还要求在正文中始终使用绝对值公式（如 `|q|E=mg`、`|q|=mg/E`），并解释低于临界电荷量时电场力不足以平衡重力。方向不能凭空假定，但可以从题目明确支持的平衡条件推导。
- 来源保护与生成准确性必须分层：canonical 原题/答案/官方解析严格只读，但 Funny Tutor 可以在新生成文本中独立给出更严谨的等价公式，不应因来源解析出现带符号表达就照抄到求电荷量大小的解释中。首题还要求明确展示 `r=1 mm=10^-3 m` 及 `r^3=(10^-3 m)^3=10^-9 m^3`。
- 公式一致性必须逐段覆盖 `funny_explanation`、`memory_aids` 和 `common_misconceptions`；JSON 字符串中的 LaTeX 反斜杠须正确转义，最终 Markdown 不得出现由 `\r` 等转义造成的断裂公式。数量级解释需准确区分：将 `1 mm` 直接当作 `1 m` 导致 `10^9` 倍体积/质量/临界电荷误差；将 `r^3` 错写为 `10^-3 m^3` 而不是 `10^-9 m^3` 则相差 `10^6` 倍。

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
- Task 7 曾进行真实单题 Smoke Test，Qwen 返回合法 JSON 但缺少 funny_explanation、将 memory_aids/common_misconceptions 生成为对象数组，并夹带 knowledge_main/knowledge_tree_path/knowledge_points；随后又出现同一链路的非 JSON 响应，说明仅依赖 Prompt 不足。当前实现已升级为 Prompt + Ollama JSON Schema structured output + Pydantic validation，并将 Generate temperature 固定为 0.0；仍需用户重新运行真实 Smoke Test 验收。
- 最新单题端到端 Smoke Test 已结构性通过：`generated=1, skipped=0, failed=0`，运行约 1m45s，Markdown 中存在 Funny Tutor 与翻车点 Callout；但内容 Gate 未通过，因为解释将电场力未经条件说明地称为“向上推力”，易错点也未优先覆盖毫米到米的换算与半径三次方。Prompt 已在 commit `3a81a7452f226ecf9d26bebcb142d8453e8588b4` 加入方向/大小、禁止补条件、单位/数量级和题目针对性约束；下一步由用户用同一题复测，质量 Gate 尚未判定通过。
- 后续单题 Smoke Test（约 1m15.7s）已改善方向推理和单位/幂次提醒，但仍在正文中混用 `q=mg/E` 与 `|q|E=mg`，且未充分解释最小阈值的因果条件。Prompt 已在 commit `cdd5dca7b0e5d519d48e2a14dd40f4941d0c3e0a` 强化：求电荷量大小时公式统一使用绝对值；若最小值对应临界平衡，应说明低于阈值时电场力为何不足以抵消重力。内容 Quality Gate 仍待用户对同一题复测。
，疑似 JSON 字符串中的 `\rho` 被解码为回车控制字符。此外，把误差描述为“数量级差三个零”不准确。Prompt 已在 commit `3156f6b44a16a6cafddbb717b8db88c66cd31996` 加强：全字段逐段公式检查、JSON/LaTeX 反斜杠转义要求，以及两类错误的精确数量级差异；SDD 验收记录也已同步。首卡 Quality Gate 仍等待下一轮真实 Qwen 复测。

## Task 2 Closure Evidence

- Runtime configuration: `qwen3.5:9b-opencode`, `think_generate=false`, `think_verify=true`, `timeout=1800s`.
- Formal A/B integration: `test_logs/test_verify_think_on_ab.log` completed 2/2 PASS. A took 840.821s; B took 1221.123s; total elapsed 2061.952s (about 34m21.95s).
- Exploratory `think=false` direct-Ollama logs remain in `test_logs/` as diagnostic evidence and are not the formal Verify acceptance path.

## Task 7 — Latest content-quality review (2026-10-09)

- Latest real single-question Smoke Test was structurally successful (`generated=1, skipped=0, failed=0`), but the content Quality Gate **failed**; structural success does not imply correct teaching content.
- Specific failures: the final explanation exposed scratch work/self-correction (“等等”“这就对上了”); it first treated approximately `4.2×10^-6` as the numerator for charge calculation, although that is the mass in kg, while the weight should be approximately `4.2×10^-5 N`; it also claimed that a larger same-kind charge could still satisfy static suspension, which conflicts with the two-force equilibrium condition. The absolute-value charge formula was not used consistently across the whole explanation.
- Prompt hardening, including the final field-reference correction, is available in commit `fb431debacf98d43df6c7648862dd29c7451f77e`. It requires a finished student-facing result without scratch/self-correction, cross-checks the expected intermediate magnitudes (`m≈4.2×10^-6 kg`, `mg≈4.2×10^-5 N`, `|q|≈4.2×10^-9 C`), and states that two-force static equilibrium requires `|q|E=mg`; force smaller/larger than weight is not static equilibrium.
- **Status remains: content Quality Gate NOT PASSED.** The user must rerun the same one-question local Qwen Smoke Test and review the rendered Markdown. Do not proceed to the 10-question batch until the explanation contains no visible scratch-work, uses mutually consistent absolute-value formulas in all three payload fields, calculates units/magnitudes correctly, and explains static equilibrium without the “more charge can still hover” claim.

## Task 7 — Follow-up review and narrow prompt revision (2026-10-09)

- Latest user-run Smoke Test after the previous prompt hardening completed structurally: `generated=1, skipped=0, failed=0`; the user-provided rendered card has consistent magnitude formulas and correct intermediate estimates (`m≈4.2×10^-6 kg`, `mg≈4.2×10^-5 N`, `|q|≈4.2×10^-9 C`). It contains no visible scratch/self-correction, and the two-force equilibrium explanation is now consistent.
- Two narrower quality issues remain: the card did not explicitly show the full evaluated identity `r^3=(10^-3 m)^3=10^-9 m^3` (showing `r=...` plus a resulting volume is insufficient for this acceptance criterion); and one misconception bullet used ambiguous language about field-line direction versus electric-force direction.
- Prompt was revised in commit `7c69e914bedd9022f988f0740d9974eaabbf259a`: the radius-cubing identity must appear explicitly and independently; `common_misconceptions` must clarify that force direction depends on charge sign and that this problem's upward electric force follows from static equilibrium, without inferring field direction or charge sign.
- **Status remains: content Quality Gate NOT PASSED pending a new one-question local Smoke Test.** Review only the two remaining requirements alongside existing formula, arithmetic, and no-scratch-work gates. Do not run the 10-question batch yet.

## Task 7 — Exact error-factor mapping follow-up (2026-10-09)

- Latest user-run single-question Smoke Test passed the previously outstanding explicit radius-cubing identity and the field-versus-force direction wording. Formula consistency, intermediate magnitudes, and removal of visible scratch work also remained correct in the supplied card.
- One acceptance issue remained: the two magnitude-error cases were combined into one misconception bullet with “(10^9) 倍或 (10^6) 倍”, rather than mapping each error to its own factor.
- Prompt was tightened in commit `f3a3ada647463e58885861d6c6ef9e712453d8bc`: when the two cases are mentioned, they must be presented separately and explicitly mapped: treating `1 mm` as `1 m` → `10^9` factor; writing `r^3=10^-3 m^3` instead of `10^-9 m^3` → `10^6` factor. Vague combined phrasing is disallowed.
- **Status remains: content Quality Gate pending one final local single-question Smoke Test.** Confirm the final card presents each case separately with its correct factor, while rechecking all previously passing gates. Do not run the 10-question batch until reviewed.

## Task 7 — Complete calculation chain and threshold wording (2026-10-09)

- The latest user-run single-question Smoke Test correctly separates the two scale errors and maps them to the correct factors (`10^9` and `10^6`); it also retains the explicit cubing identity and correctly explains field direction versus electric-force direction.
- Two final teaching-content gaps remain: the explanation gives the formulas `m=ρV` and `|q|=mg/E` but does not spell out all four numerical stages (volume, mass, weight, charge magnitude); and the threshold phrase should explicitly say “电场力不足以平衡重力，雨滴无法保持静止”, avoiding ambiguous wording such as “支撑雨滴下落”.
- Prompt updated in commit `241be98c882715847c46c266e0a1ed80aabe9148`: Generate must show the full numeric chain (`V≈4.2×10^-9 m^3`, `m≈4.2×10^-6 kg`, `mg≈4.2×10^-5 N`, `|q|≈4.2×10^-9 C`) with quantities and units, and use the unambiguous equilibrium statement for sub-threshold charge.
- **Status remains: content Quality Gate pending another local single-question Smoke Test.** Review the complete numerical chain and threshold wording in addition to previously passed gates. Do not run the 10-question batch until reviewed.

## Prompt-churn review and stop policy (2026-10-09)

### Findings from repeated single-question Smoke Tests

- The repeated iterations have progressively fixed real defects (signed-vs-magnitude formulas, arithmetic scratch work, force direction, explicit radius cubing, magnitude-factor mapping, and complete numeric calculation). This is useful fault discovery, but the workflow is at risk of **overfitting one question and endlessly appending natural-language rules**.
- The current `FunnyTutorPayload` Pydantic schema and Ollama JSON Schema constrain shape and types; they do **not** prove that a physics explanation is correct, complete, student-facing, or free of contradictory claims. That is an enforcement-boundary gap, not something a longer Prompt alone can guarantee.
- The tested local model (`qwen3.5:9b-opencode`, CPU-only per current setup) has shown partial compliance and improvement, but sometimes misses a nearby requirement while satisfying others. This is consistent with limited instruction-following under a dense prompt; the evidence does not establish that model capability is the sole cause.
- A second design issue is that a shared system Prompt contained question-specific rain-drop constants and required calculations. Those requirements could leak into other questions in the 10-item bank. Commit `7715fb8c92076e6786cf5c5801168deec92aad67` scopes the rain-drop rules to the matching item and defines exactly three student-facing misconception entries for it.
- A third issue is that visual/manual inspection of a single output has been acting as the primary quality gate. One carefully tuned case is not evidence that the same Prompt generalizes to nine different questions.

### Decision: stop rule to prevent endless Prompt edits

1. Treat commit `7715fb8c92076e6786cf5c5801168deec92aad67` as the **Prompt-freeze candidate**. Run one more Smoke Test on the existing rain-drop item to verify the exact three-item misconception structure and ensure no internal instructions leak into the student card.
2. If that test passes, do not keep tuning this Prompt for minor wording preferences. Freeze the Prompt and run a **3-question pilot**: the rain-drop item plus two distinct questions selected from the remaining bank, ideally with different reasoning/units. Record results in a pass/fail matrix.
3. For failures, classify them instead of automatically rewriting the shared Prompt:
   - JSON keys/types/extra fields → existing schema/structured-output boundary.
   - Explicit, deterministic constraints (required values/phrases, list count, forbidden meta-instructions) → add a small post-generation validator and tests where practical.
   - Physics validity, omitted reasoning, or subtle contradictions → independent reviewer/checklist and manual review; do not assume JSON Schema can catch semantics.
   - Cosmetic wording differences with correct meaning → accept, not a defect.
4. Limit the pilot to **at most one Prompt revision** after the freeze candidate. Reopen a shared Prompt rule only if the same material defect recurs in at least two distinct questions, or a single critical physics error warrants immediate correction. If an individual question still fails, mark it for review instead of entering an automatic retry loop.
5. After the 3-question pilot, generate the remaining questions once, inspect all ten outputs with a fixed rubric, and mark any failing card for manual correction/review. No unbounded retries and no batch processing that silently treats generation success as content-quality success.

### Root-cause assessment

The evidence points to a combination rather than a single cause: smaller local-model instruction-following limits; the fragility of asking one generation call to both create and self-audit prose; over-specific rules sharing one Prompt; and missing automated semantic/regression checks. The next improvement should be a layered quality gate and representative evaluation set, not an indefinitely longer Prompt.


## Quality Gate v1 — Candidate, Review, Publish (2026-10-10)

### Decision

- Treat all LLM output as a candidate. No model confidence value is accepted as proof.
- Separate deterministic text/schema checks from semantic physics review.
- Require two distinct reviewer model identifiers for automatic ACCEPT; duplicate calls under the same model identifier do not count as independent reviewers.
- A hard, evidence-backed FAIL in any review dimension results in REJECT. Missing reviewers, answer disagreement, canonical-answer mismatch, or any UNCERTAIN result results in REVIEW. Only all-PASS reports with independent answers matching the canonical answer can result in ACCEPT.
- These states express evidence thresholds, not absolute correctness guarantees. Reviewer diversity is a heuristic; different model names do not prove statistical independence.

### Implementation

- `src/quality_gate.py`: rejects generated control characters other than LF and deterministically aggregates structured review reports.
- `src/schema.py`: defines strict review check, independent solution, review report, and publication decision schemas.
- `src/prompts/independent_solver.txt`: first-pass solve prompt that must be run before showing the reference answer or candidate content.
- `src/prompts/review_gate.txt`: bounded structured reviewer prompt; asks for evidence and explicit PASS/FAIL/UNCERTAIN per dimension.
- `src/review_gate.py`: validates saved review input and writes a machine-readable decision plus evidence.
- `src/publish_reviewed.py`: promotes a staged Markdown card only if the matching decision is ACCEPT and its evidence contains at least two distinct reviewer IDs with all required checks PASS.
- `src/llm_client.py`: rejects decoded generated text containing forbidden control characters before it reaches the renderer. This catches JSON escapes such as an unescaped `\\r` becoming a carriage return, but it does not replace review of LaTeX semantics.

### Operational boundary

The current CLI aggregates saved review evidence; it does not automatically call two models or guarantee that the first-pass solver and reviewer stages were executed in the required order. The operator must preserve the first-pass result before giving the same reviewer access to canonical answer/analysis or candidate content. Model orchestration and provenance are future work. Generated cards remain staged candidates until explicitly promoted.


- **Default-path safeguard:** `config.toml` now writes generated cards to `vault/FunnyTutor_EM_Candidates`, not the formal `vault/FunnyTutor_EM_Vault`. The explicit publisher is the intended promotion path.

## 1.0 Traceability Review — Authoritative Status (2026-10-11)

This section supersedes earlier historical checklist entries where their status wording is stale. Historical Task 7 smoke-test notes are retained as a record of why the quality gate was added; they are not a requirement to keep tuning the Prompt until Qwen passes every semantic check.

| Workstream | Implementation status | Validation status | Decision |
|---|---|---|---|
| Task 1 — Schema / repository foundation | Complete | User reports `ruff` and `pytest` PASS; schema tests exist | Complete |
| Task 2 — LiteLLM client and Generate/Verify mode | Complete as a client abstraction | Local Qwen Verify A/B evidence is recorded; provider comparison is not run | Complete for 1.0 pipeline |
| Task 3 — Markdown renderer | Complete | Renderer tests exist; real Obsidian formula/image display not yet signed off | Implemented; GUI check deferred |
| Task 4 — Daily index | Complete | Unit tests cover uniqueness, bounds, and rendering | Complete |
| Task 5 — Pipeline, assets, incremental/force | Implemented | Integration tests cover generate, skip, force, failure continuation, dry-run; stale-card failure case added in latest change and awaits local test | Implemented; run latest regression suite |
| Task 6 — Legacy to Canonical import | Complete for current fixture | Prior local evidence: 10 records converted, dry-run succeeded; annotation placeholders remain | Complete as adapter, not curated data |
| Task 7 — Strict Generate output contract | Structural implementation complete | Real Qwen pilot has at least one malformed-text rejection and two content-level defects | Pipeline contract complete; content defects moved to tech debt |
| Task 8 — Review evidence and publication | CLI/schema/prompt/tests implemented | Operator-run review CLI/publisher fixtures and real reviewed publication are not yet evidenced | Manual release workflow; validation remains |
| 1.0 end-to-end | Main components are connected and pilot calls have run | Three-question pilot was not all successful; latest code change needs local test | **Engineering 1.0 candidate, not content-approved release** |

### 1.0 close-out rule

Do not block the pipeline milestone on making local Qwen perfect. Close the engineering loop by validating generation, failure isolation, incremental rerun, dashboard links, and candidate/publish separation. Then run the same fixed questions through Qwen and cloud models and record comparative outcomes. Never promote cards with unresolved critical errors; content failures are reviewed/corrected per card, not an invitation for unbounded shared-Prompt edits.
