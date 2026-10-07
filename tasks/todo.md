# tasks/todo.md

## Task 1: 项目骨架初始化与数据模型 Schema

**Description:** 创建标准目录结构、配置文件，并使用 Pydantic 定义核心数据结构（KnowledgePoint 和 EMQuestion），把好数据的入口关。

**Acceptance criteria:**
- [ ] 目录结构（src, tests, data/assets, vault）及 requirements.txt、config.toml 创建完毕。
- [ ] EMQuestion 准确覆盖 Spec 中的所有字段。
- [ ] 校验逻辑能正确拒收缺少必填字段或类型错误的 JSON 片段。

**Verification:**
- [x] Tests pass: pytest tests/test_schema.py -v (11 passed)
- [x] Manual check: config.toml 已提供 LiteLLM 路由配置，默认本地 Ollama/Qwen3.5:9b 与 Vault 路径。

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
