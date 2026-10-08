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
- [ ] 检查首卡内容：原题、答案和官方解析来源字段保持原样；AI 新生成的教学解释不受“来源字段只读”限制，可以独立给出严谨的等价公式。电场力方向不得凭空假定，但可从悬浮平衡条件推导其与重力方向相反；求电荷量大小时，生成内容应统一使用绝对值（`|F_E| = |q|E`、`|q|E = mg`、`|q| = mg/E`），不得无说明地混用 `q` 与 `|q|`；解释最小值时，需说明低于阈值为什么电场力不足以平衡重力；必须明确展示 `r = 1 mm = 10^-3 m` 和 `r^3 = (10^-3 m)^3 = 10^-9 m^3`，而非泛泛提醒换算单位。以上不满足时不得进入 10 题批量生成。
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
