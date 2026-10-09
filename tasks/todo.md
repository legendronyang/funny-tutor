# tasks/todo.md

## Task 1: 项目骨架初始化与数据模型 Schema

**Description:** 创建标准目录结构、配置文件，并使用 Pydantic 定义核心数据结构（KnowledgePoint 和 EMQuestion），把好数据的入口关。

**Acceptance criteria:**
- [ ] 目录结构（src, tests, data/assets, vault）及 requirements.txt、config.toml 创建完毕。
- [ ] EMQuestion 准确覆盖 Spec 中的所有字段。
- [ ] 校验逻辑能正确拒收缺少必填字段或类型错误的 JSON 片段。

**Verification:**
- [x] Tests pass: pytest tests/test_schema.py -v (11 passed)
- [x] Manual check: config.toml 已提供 LiteLLM 路由配置，默认本地 Ollama/Qwen3.5:9b-opencode 与 Vault 路径。

**Dependencies:** None

**Files likely touched:**
- requirements.txt
- config.toml
- pytest.ini
- src/schema.py
- tests/test_schema.py

**Estimated scope:** Small: 3-4 files

### 

## Task 2: LiteLLM 大模型客户端、JSON 清洗与 Generate/Verify 契约

**Description:** 编写统一 LLM Client，通过 LiteLLM 路由模型；开发阶段默认使用 WSL Ubuntu 中的 Ollama `ollama_chat/qwen3.5:9b-opencode`。Generate 默认关闭 thinking 以控制 CPU 延迟，Verify 默认开启 thinking 以保证独立求解。客户端负责加载 Prompt、调用模型、稳定提取结构化 JSON，并提供 generation / verification 所需的最小接口。业务代码不得依赖具体 provider。

**Acceptance criteria:**
- [x] 正确读取配置中的 LiteLLM model/api_base；云端 API Key 通过环境变量读取，本地 Ollama 不要求 API Key。
- [x] 实现针对大模型返回内容的清洗方法，能够稳定剥离外壳提取 JSON。
- [x] 当 JSON 解析彻底失败时，抛出包含题目 ID 的明确自定义异常。
- [x] generation / verification 模式契约明确：空目标字段生成；已有可信字段必须独立求解后再比较，不得把 provided answer 当作推理依据。
- [x] LLM provider/model 可仅通过配置切换，不修改上层业务代码。

**Verification:**
- [x] Tests: `pytest tests/test_llm_client.py -v` 已验证 15 tests；当前配置切换到 `qwen3.5:9b-opencode` 后同步更新了配置断言。当前代码快照的隔离复现测试结果为 15 passed。
- [x] Manual check: Prompt 包含“绝不改写 LaTeX”“独立求解后再验证”“仅输出 JSON”等强制指令。
- [x] Manual integration: 使用正式 `LLMClient -> LiteLLM -> Ollama -> qwen3.5:9b-opencode` 链路、`think_verify=true`、`timeout=1800s` 完成 A/B Verify；A=正确答案 B -> `B/match`，B=故意错误答案 D -> `B/mismatch`，2/2 PASS。正式证据见 `test_logs/test_verify_think_on_ab.log`，总耗时约 34m22s（A 14m00.821s，B 20m21.123s）。
- [x] Runtime decision: 本地 CPU 开发阶段采用 `qwen3.5:9b-opencode`；Generate `think=false`，Verify `think=true`，`timeout=1800`。`think=false` 的 direct diagnostic 已作为探索性记录保留，但不作为正式 Verify 策略验收依据。

**Dependencies:** Task 1

**Files likely touched:**
- src/llm_client.py
- src/prompts/funny_tutor_em.txt
- tests/test_llm_client.py
- config.toml
- requirements.txt

**Estimated scope:** Medium: 4-6 files

### 
## Task 3: Markdown 卡片渲染器

**Description:** 实现纯函数将 Python 字典拼接为符合 Obsidian 语法的 Markdown 文本。

**Acceptance criteria:**
- [ ] 文本中正确包含 Callout 语法。
- [ ] 保留输入数据中的所有 LaTeX 源码片段。
- [ ] 依据 images_paths 将图片拼接为指向沙盒资产目录的相对路径。
- [ ] 依据 knowledge_tree_path 在文首或文末追加双链。

**Verification:**
- [ ] Tests pass: pytest tests/test_renderer.py -v
- [ ] Manual check: 检查测试用例输出的 Markdown 字符串结构合法性。

**Dependencies:** Task 1

**Files likely touched:**
- src/markdown_renderer.py
- tests/test_renderer.py

**Estimated scope:** Small: 2 files

### 

## Task 4: 每日看板随机抽题逻辑

**Description:** 实现纯函数，基于题库总列表，随机选取指定数量的题目 ID，生成看板需要的文本片段。

**Acceptance criteria:**
- [ ] 确保抽取的题目互不重复。
- [ ] 边界条件处理：如果请求的题目数大于题库总数，返回全部题目列表而不报错。

**Verification:**
- [ ] Tests pass: pytest tests/test_daily_index.py -v
- [ ] Manual check: 多次调用函数确认返回结果具有随机性。

**Dependencies:** Task 1

**Files likely touched:**
- src/daily_index.py
- tests/test_daily_index.py

**Estimated scope:** Extra Small: 2 files

### 

## Task 5: 核心主控脚本与资产同步（Pipeline）

**Description:** 编写 generate_vault.py 作为系统总入口，调度所有子模块，实现资产文件的复制同步、增量判定逻辑，以及文件 I/O 写入。

**Acceptance criteria:**
- [ ] 启动时自动将 data/assets/ 下的图片同步到 vault/.../assets/ 中。
- [ ] 根据 knowledge_tree_path 自动在 Vault 中创建缺失的各级知识点目录。
- [ ] 增量判定：在未添加 force 参数时，若某题对应的 md 文件已存在，则打印跳过信息，不调用 LLM。
- [ ] 异常跳过：若 LLM 解析异常，脚本记录日志后继续处理下一题。
- [ ] 最终覆盖生成 00_今日电磁学吐槽.md 看板文件。

**Verification:**
- [ ] Tests pass: pytest tests/ -v
- [ ] Build succeeds: 使用包含 3 道题目的迷你 JSON 运行主脚本。
- [ ] Manual check: 执行两次主脚本观察增量跳过逻辑，在 Obsidian 中打开验证排版与图片加载。

**Dependencies:** Task 2, Task 3, Task 4

**Files likely touched:**
- src/generate_vault.py
- data/assets/ (读取)
- vault/ (写入)

**Estimated scope:** Medium: 1-2 files
---

## Task 6: 旧题库导入适配器与 Canonical Schema 转换

**背景与问题：**

Task 5 的主管道在导入模块时已可正常启动，但执行 Dry-run 时，`data/questions_em.json` 中的历史 OCR 题目记录无法通过 `EMQuestion` 校验。原始记录使用 `category`、`question`、`analysis` 等来源字段，并缺少标准模型要求的 `id`、`subject`、`question_type`、知识树、知识点和难度等字段。49 项单元测试此前全部通过，是因为主管道测试使用了符合 Canonical Schema 的模拟题目，没有覆盖真实的旧格式输入。

不能通过放宽 `EMQuestion` 必填约束来掩盖问题，也不能让 LLM 或导入脚本悄悄编造知识标注。应在原始来源与主管道之间增加一个显式、可重复、可测试的转换边界。原始文件保留不动，转换结果写入独立的 Canonical JSON 文件；缺少可靠标注的字段必须使用醒目的待标注占位符并在导入报告中披露，不能把占位值误认为已确认的教学内容。

**Description：**

新增 `src/import_questions.py`，将现有 OCR/历史格式题库转换为 `EMQuestion` 标准结构。为题目生成确定性 ID，映射来源字段，保留原始题干、答案和官方解析，输出前使用 Pydantic 完整校验并检查 ID 唯一性。缺少的知识点、难度和题型信息明确标记为待人工确认。更新 `config.toml`，让 Vault Generator 读取转换后的 `data/questions_em_canonical.json`，而不是直接读取旧格式来源文件。

**Acceptance criteria：**

- [x] 原始 `data/questions_em.json` 不被覆盖或修改。
- [x] 转换脚本能把当前旧格式题库转换成标准 `EMQuestion` JSON。
- [x] 同一条来源记录重复转换会产生相同 ID；不同记录的 ID 必须唯一，否则转换失败。
- [x] 题干中的 LaTeX、答案和官方解析按原文保留。
- [x] 不推断或伪造知识点、难度和题型；缺失信息使用明确的待标注占位符并在报告中统计。
- [x] 输入字段缺失、JSON 顶层类型错误或标准模型校验失败时，转换失败且不写出不完整的输出文件。
- [x] `config.toml` 的 `questions_json` 指向转换后的 Canonical JSON 文件。
- [x] `ruff check src tests` 和 `pytest tests/ -v` 通过。

**Verification：**
- [x] 执行 `python src/import_questions.py`：生成 10 条 Canonical 记录，并报告知识点、难度、题型均待复核。
- [x] 执行 `python src/generate_vault.py --config config.toml --dry-run`：total=10、failed=0。
- [x] 检查转换结果并确认原始 `data/questions_em.json` 未被修改；`git diff -- data/questions_em.json` 无输出。
- [x] 在人工补齐知识标注前，Smoke Vault 使用明确的“待标注”占位节点。

**Dependencies：** Task 1（Schema）、Task 5（Pipeline 输入契约）

**Files likely touched：**
- `src/import_questions.py`
- `tests/test_import_questions.py`
- `config.toml`
- `data/questions_em_canonical.json`（运行时生成，不要求提交生成数据）

**Estimated scope：** Medium: 3-4 files


## Task 7: LLM Generate 输出契约强化与真实 Smoke Test

**背景与问题：**

Task 6 已打通真实旧题库到 Canonical Schema。随后进行真实单题 Generate Smoke Test 时，Qwen 返回了合法 JSON，但输出了不属于 Generate 任务的 knowledge_main、knowledge_tree_path、knowledge_points，缺少 funny_explanation，并将 memory_aids、common_misconceptions 生成为对象数组。仅依赖 JSON extraction 会把这种响应误判为成功。

**目标：**

严格区分“JSON 可解析”和“业务响应合规”，并将模型输出约束从 Prompt 单层约束升级为“Prompt + Ollama JSON Schema + Pydantic validation”三层边界。

Generate 模式必须输出 FunnyTutorPayload；LLM Client 和 Vault 写入边界都要校验；renderer 只能接收白名单字段。Prompt 必须明确输出 schema 与禁止字段。

**Acceptance criteria：**
- [ ] FunnyTutorPayload 使用严格 Pydantic 校验：三个字段必需，列表项为字符串，memory_aids/common_misconceptions 各 1–3 条，禁止额外字段。
- [ ] Generate 模式的 LLMClient.complete_json() 在 JSON extraction 后执行 FunnyTutorPayload 校验；失败异常包含题目 ID。
- [ ] generate_vault.py 在写 Markdown 前再次校验 Generate payload，并采用字段白名单合并。
- [ ] Generate Prompt 明确列出完整 JSON schema、字段类型、禁止字段和只读输入约束。
- [ ] Ollama `ollama_chat` Generate 请求传递 FunnyTutorPayload JSON Schema，并将 temperature 固定为 0.0。
- [ ] 自动化测试覆盖缺字段、额外字段、错误嵌套类型、非法 Generate response 不写卡。
- [ ] ruff check src tests 和 pytest tests/ -v 通过。
- [ ] 真实 Qwen 单题 Smoke Test 返回严格合法的 Generate payload，并生成包含 Funny Tutor callout 的 Markdown 卡片。
- [ ] 首卡通过内容 Quality Gate：不臆断题干未给出的方向/符号；核心关系表述严谨；单位、幂次和数量级陷阱经过检查；易错点具体且与本题相关。

**Verification：**
- [ ] 本地执行 pytest tests/ -v。
- [ ] 本地执行 ruff check src tests。
- [ ] 重新执行一题 Smoke Test，确认错误模型响应被明确拒绝；符合契约时生成 [!tip] Funny Tutor 和 [!warning] 翻车点。
- [ ] 检查首卡内容：原题、答案和官方解析来源字段保持原样；AI 新生成的教学解释可以独立给出严谨等价公式。方向可从题目支持的平衡条件推导，但不得凭空假定；求电荷量大小时，`funny_explanation`、`memory_aids`、`common_misconceptions` 全部段落都必须一致使用绝对值（`|F_E| = |q|E`、`|q|E = mg`、`|q| = mg/E`），不允许正文残留无说明的 `mg = Eq` 或 `Eq = ... × q`。必须明确展示 `r = 1 mm = 10^-3 m` 及 `r^3 = (10^-3 m)^3 = 10^-9 m^3`；准确区分直接将 mm 数值当 m 导致 `10^9` 倍误差与把立方结果写成 `10^-3 m^3` 导致 `10^6` 倍误差。检查最终 Markdown 中 LaTeX 是否完整，特别是 `\rho` 是否被错误解码成回车后残留 `ho`；JSON 源字符串中的反斜杠必须正确转义。以上不满足时不得进入 10 题批量生成。
- [ ] 确认原始 data/questions_em.json 仍未变化。
- [ ] 完成以上验证后，才进入 10 题全量 Generate。

**Dependencies：** Task 2、Task 3、Task 5、Task 6

**Files likely touched：**
- src/schema.py
- src/llm_client.py
- src/generate_vault.py
- src/prompts/funny_tutor_em.txt
- tests/test_schema.py
- tests/test_llm_client.py
- tests/test_generate_vault.py
- spec.md
- tasks/plan.md
- tasks/todo.md

**Estimated scope：** Medium

### Task 7 — 最新内容质量门记录（2026-10-09）

- [x] 根据最近一次真实 Smoke Test 记录内容质量问题；该测试结构上成功，但内容质量门仍失败。
- [x] 强化 Generate Prompt：最终卡片不得包含“等等”“我算错了”“这就对上了”等试算、自我怀疑或自我纠错叙述。
- [x] 强化数值不变量复核：本题应有 `m≈4.2×10^-6 kg`、`mg≈4.2×10^-5 N`、`|q|≈4.2×10^-9 C`，不得把质量当作重力直接用于 `|q|=mg/E`。
- [x] 强化两力静止平衡约束：必须满足 `|q|E=mg`；电场力小于重力不足以平衡，大于重力则不是静止平衡。
- [ ] 用同一道题重跑本地 Qwen 单题 Smoke Test，人工复核最终 Markdown 中三个 payload 字段的公式一致性、计算量纲/数量级、无草稿式纠错，以及静止平衡解释。
- [ ] 在上述内容质量门通过前，不允许执行 10 题批量生成。

对应 Prompt 修改提交（含最终字段引用修正）：`fb431debacf98d43df6c7648862dd29c7451f77e`。

### Task 7 — 第二轮 Smoke Test 后的小修正（2026-10-09）

- [x] 记录上一轮卡片已修复的内容问题：正文无可见自我纠错；绝对值公式一致；质量、重力与电荷量数量级正确；两力静止平衡解释正确。
- [x] Prompt 强制完整、独立地输出 `r^3=(10^-3 m)^3=10^-9 m^3`；不能仅由半径换算和体积近似值让学生反推。
- [x] Prompt 强制 `common_misconceptions` 准确区分电场方向与电场力方向：电场力方向还取决于电荷正负；本题电场力向上来自静止平衡条件，不能据此单独确定电场方向或电荷正负。
- [ ] 使用同一单题配置重新运行本地 Qwen Smoke Test，确认完整立方等式实际出现在卡片中，方向易错点表达清楚，并复查既有质量/公式 Gate。
- [ ] 在新的单题验收通过前，不执行 10 题批量生成。

Prompt 修改提交：`7c69e914bedd9022f988f0740d9974eaabbf259a`。

### Task 7 — 两种数量级错误分别映射（2026-10-09）

- [x] Prompt 已要求两种错误分别作为独立易错点呈现，不允许只写“`10^9` 倍或 `10^6` 倍”。
- [x] 明确误差映射：将 `1 mm` 直接当成 `1 m` 代入 → 体积/质量/临界电荷量放大 `10^9` 倍；把 `r^3` 写成 `10^-3 m^3` 而非 `10^-9 m^3` → 放大 `10^6` 倍。
- [ ] 使用同一单题配置重新运行本地 Qwen Smoke Test，确认最终卡片将两种错误分开、倍率逐项对应，并复核此前已通过的物理公式、数值、立方等式、方向解释和无草稿式纠错要求。
- [ ] 最终单题内容质量门通过前，不执行 10 题批量生成。

Prompt 修改提交：`f3a3ada647463e58885861d6c6ef9e712453d8bc`。

### Task 7 — 完整数值链与临界条件措辞（2026-10-09）

- [x] Prompt 要求 Funny Tutor 正文完整展示体积、质量、重力、电荷量大小四阶段数值及单位：`V≈4.2×10^-9 m^3`、`m≈4.2×10^-6 kg`、`mg≈4.2×10^-5 N`、`|q|≈4.2×10^-9 C`。
- [x] Prompt 明确要求使用“电场力不足以平衡重力，雨滴无法保持静止”的表述，避免“电场力不足以支撑雨滴下落”等含糊措辞。
- [ ] 使用同一单题配置重新运行本地 Qwen Smoke Test，确认生成正文真的包含完整四阶段数值链和准确的临界条件表达，并复核此前所有质量门。
- [ ] 最终单题内容质量门通过前，不执行 10 题批量生成。

Prompt 修改提交：`241be98c882715847c46c266e0a1ed80aabe9148`。

### Prompt 冻结候选与防止无限迭代（2026-10-09）

- [x] 对指定雨滴题规定固定的 3 条 `common_misconceptions`：方向判断、毫米误当米（`10^9` 倍）、立方指数错误（`10^6` 倍）；禁止把 Prompt 内部约束原样写进学生卡片。
- [x] 明确雨滴专属数值规则只适用于对应题目，避免污染题库中其余题目。
- [x] 将临界平衡验收改为语义判断：允许自然、等价的学生用语，不因没有逐字复现固定句子而继续调整 Prompt。
- [x] 在 Plan 记录停止规则：当前提交作为 Prompt 冻结候选；单题通过后先做 3 题代表性 pilot；最多允许 pilot 后一次 Prompt 修订；对仍不通过的单题标记人工复核，不无限重试。
- [ ] 本地复测雨滴题：确认易错点恰好 3 条、三条均为学生错误/正确思路、没有“严禁出现……”等元指令泄漏；并复核公式、四阶段数值链和物理方向。
- [ ] 单题通过后，选择另外两道不同题型/推理结构的题目，完成 3 题 pilot 并记录结果矩阵。
- [ ] Pilot 通过后再生成其余题目；每题仅生成一次，按固定 rubric 逐题验收，失败项进入人工复核，不自动无限重试。

Prompt 冻结候选提交：`7715fb8c92076e6786cf5c5801168deec92aad67`；防无限迭代评审记录：`40e3f71c89c9b6bd46caab2014abfaa5bdef5edf`。
