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
- Prompt hardening was checked in at commit `38520f2bcd4c7b8510afb46ab041ae3d2e712410`. It requires a finished student-facing result without scratch/self-correction, cross-checks the expected intermediate magnitudes (`m≈4.2×10^-6 kg`, `mg≈4.2×10^-5 N`, `|q|≈4.2×10^-9 C`), and states that two-force static equilibrium requires `|q|E=mg`; force smaller/larger than weight is not static equilibrium.
- **Status remains: content Quality Gate NOT PASSED.** The user must rerun the same one-question local Qwen Smoke Test and review the rendered Markdown. Do not proceed to the 10-question batch until the explanation contains no visible scratch-work, uses mutually consistent absolute-value formulas in all three payload fields, calculates units/magnitudes correctly, and explains static equilibrium without the “more charge can still hover” claim.
