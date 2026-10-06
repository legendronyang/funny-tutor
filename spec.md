# Spec: Funny Tutor - EM Vault Generator（电磁学 Obsidian 题库生成器）

## ASSUMPTIONS I'M MAKING

1. 开发与运行环境为本地纯 Python 环境（Python 3.10+），运行在 Windows 11 的 WSL Ubuntu 中，不构建 Web 后端或数据库。
2. 源数据 questions_em.json 在本项目边界之外通过人工或 OCR 工具准备好并确保格式合法；本项目从“读取合法 JSON”开始，不负责 OCR 或题目抓取。
3. 项目中存在一个 llm_client.py，封装对 Google Gemini 的调用（可基于官方 API 或 CLI），API Key 等凭证通过 .env 或环境变量读取，严禁硬编码在代码或仓库中。
4. MVP 只服务于电磁学（电磁感应、交流电等高二上学期内容），题量在几十道规模以内（目标是先打通端到端流程）。
5. 呈现端仅为 Obsidian，大量使用 [[双链]] 与 > [!tip] 等 callout 语法，但不强依赖第三方插件。
6. 单机 / 单 Vault 场景（可由一个学生或家庭共用），不考虑账号系统、多用户权限或跨设备同步（交由 Obsidian Sync 或网盘解决）。
7. 生成操作必须是增量的：日常运行脚本刷新“今日任务”或重新扫描题库时，不得对已有题卡重复发起 LLM 请求，除非显式指定 --force 或等价选项。
8. MVP 阶段仅使用 Pydantic 做 Schema 校验，不额外维护 JSON Schema 文件。

如果这些假设不符，需要先更正；否则以下内容以此为前提。

## Objective

构建一个轻量、可重复运行且增量友好的 Python 批处理管道，以结构化电磁学真题 JSON 为题库真相源（Canonical Model），通过 LLM 生成 Funny Tutor 风格的解释与记忆钩子，并产出：

1. 题卡片（每题一页的 Obsidian Markdown）
   - 内容组件：
     - 原题干（含 LaTeX 与图片引用）
     - 官方 / 权威解析（analysis_official）
     - LLM 生成的大白话解释（funny_explanation）
     - 记忆钩子（memory_aids）
     - 易错点提示（common_misconceptions）
   - 结构特征：
     - 保留原始 LaTeX 公式和物理量标记，LLM 不得改写公式。
   - 使用 Obsidian 标签与 [[双链]] 接入统一知识树（knowledge_tree_path）。

2. 每日任务看板（文件名 00_今日电磁学吐槽.md）
   - 每次运行脚本时，根据题库简单随机选出 3–5 道题目，生成带双链的当日任务列表。
   - 不调用 LLM，只读取现有题卡和题库，实现“一键打开即可开始微学习”。

## Tech Stack

- 语言与运行环境
  - Python 3.10+（WSL Ubuntu 环境）。

- 核心库
  - pydantic：定义并校验题库 JSON 的 Schema（EMQuestion、KnowledgePoint 等）。
  - python-dotenv：从 .env 文件加载环境变量（如 API Key）。
  - Gemini 客户端：
    - 使用 llm_client.py 作为统一封装；内部可以是：
      - 基于 google-genai 的官方 SDK，或
      - 基于 CLI 的子进程封装。
    - 对上层暴露统一的 Python 函数接口（不直接散落使用 CLI 或 SDK）。

- 开发工具
  - pytest：单元测试。
  - ruff：静态检查与格式统一。

## Commands

建议的命令接口（可按仓库实际结构微调，但要保持一致性与可复制性）：

- 安装依赖：
  pip install -r requirements.txt

- 正常运行（增量构建）：
  python src/generate_vault.py --config config.toml

- 强制全量重建（忽略已有题卡，重新请求所有题的 LLM）：
  python src/generate_vault.py --config config.toml --force

- 干运行（仅校验 JSON 与路径，不调用 LLM、不写文件）：
  python src/generate_vault.py --config config.toml --dry-run

- 运行测试：
  pytest tests/ -v

- 代码风格检查：
  ruff check src tests
  ruff check --fix src tests
## Project Structure

项目目录建议如下（以仓库根目录为基准）：

- config.toml
  全局配置（支持多 Vault），包括 LLM 配置与每个 Vault 的输入输出路径等。

- .env
  本地环境变量（API Key 等），应在 .gitignore 中忽略。

- data/
  - questions_em.json
    电磁学题库真相源，符合 Pydantic 定义的 Schema。
  - assets/
    - em_diagrams/
      电路图、波形图等图片资源，源文件存放在此。

- src/
  - schema.py
    Pydantic 模型定义，例如 KnowledgePoint、EMQuestion，约束 JSON 结构。
  - llm_client.py
    Gemini 客户端封装，负责构造 Prompt、发起调用、提取并解析结构化 JSON。
  - markdown_renderer.py
    纯函数模块，将 EMQuestion 与 LLM 输出组合为 Obsidian Markdown 字符串。
  - daily_index.py
    纯函数模块，实现简单随机抽题逻辑。
  - generate_vault.py
    主入口脚本：解析 config.toml、同步图片资产、执行增量构建、调度 LLM 与渲染、写出题卡和首页。
  - prompts/
    - funny_tutor_em.txt
      System Prompt 与 Few-shot 模板，约束 LLM 行为。

- tests/
  - test_schema.py
    验证 JSON 数据结构及必需字段。
  - test_renderer.py
    验证 Markdown 模板拼接、LaTeX 原样插入与 Callout 语法。
  - test_llm_client.py
    使用 mock LLM 响应，测试 JSON 剥离与解析逻辑。
  - test_daily_index.py
    验证简单随机抽题策略的行为。

- vault/
  - FunnyTutor_EM_Vault/
    - 00_今日电磁学吐槽.md
      每日任务首页（每次运行覆盖）。
    - assets/
      脚本运行时自动从 data/assets/ 同步过来的图片资源（供 Obsidian 沙盒内渲染使用）。
    - 其他按 knowledge_tree_path 自动生成的子目录与题卡 Markdown 文件。

## Data Model（Pydantic Schema）

以下示例仅说明字段与风格，具体可在实现阶段小幅调整：

    from typing import List, Optional
    from pydantic import BaseModel

    class KnowledgePoint(BaseModel):
        id: str
        name: str
        summary_plain: str
        prerequisites: List[str] = []
        typical_pitfalls: List[str] = []

    class EMQuestion(BaseModel):
        id: str
        year: str
        paper: str
        subject: str
        index: int
        score: int
        question_type: str                # 例如 "single_choice", "fill_blank"
        question_raw: str
        options: Optional[list[dict]] = None
        answer: list[str]
        analysis_official: str
        images_paths: list[str] = []
        knowledge_main: str
        knowledge_tree_path: list[str]    # 按固定电磁学知识树
        knowledge_points: list[KnowledgePoint]
        exam_tags: list[str] = []
        difficulty: int                   # 建议 1–5 级

        # 以下字段在 LLM 生成前可以为空，生成后写入 Markdown，不要求写回 JSON
        memory_aids: list[str] = []
        funny_quick_tip: Optional[str] = None
        common_misconceptions: list[str] = []

说明：
- 题库 JSON 作为“真相源”，至少要完整覆盖题目、解析与知识结构字段。
- LLM 输出若只写入 Markdown 而不写回 JSON，MVP 可以接受；缓存机制可作为后续优化。

## LLM 输出格式与 llm_client 契约

为保证精确性和 token 经济性，LLM 的输出统一为结构化 JSON，由 llm_client.py 解析为 Python dict，再交给渲染模块。
### 单题目标输出结构

    {
      "funny_explanation": "一段大白话解释...",
      "memory_aids": [
        "顺口溜或类比 1",
        "顺口溜或类比 2"
      ],
      "common_misconceptions": [
        "典型翻车点 1",
        "典型翻车点 2"
      ]
    }

字段约束：
- funny_explanation：字符串，可多句，不含复杂 Markdown 结构，由渲染模块负责包裹为 Callout 内容。
- memory_aids：字符串列表，建议长度 1–3，每条简短有力。
- common_misconceptions：字符串列表，建议长度 1–3，聚焦概念性与方法性的易错点。

### llm_client.py 的责任

- 提供核心函数（示意）：
      def generate_funny_payload(question_context: dict) -> dict:
          # 输入: question_context (包含题干、解析等)
          # 输出: 结构化 JSON 字典 (funny_explanation, 等)
          pass

- 函数内部应当：
  - 从 prompts/funny_tutor_em.txt 载入 System Prompt 与 Few-shot 示例。
  - 通过 Gemini（API 或 CLI）发起调用。
  - 对返回文本执行“剥离 JSON”逻辑：
    - 能处理“纯 JSON 文本”或“被 Markdown 代码块包裹的 JSON 文本”两种情况（注意：解析时必须使用正则如 r"^" + r"```" + r"json" 或字符串方法去壳，防止被 Markdown 解析器截断）。
    - 提取第一个看起来是 JSON 对象的片段，再用 json.loads 解析。
  - 在解析失败时抛出明确的异常，描述题目 ID 与失败原因，上层可据此跳过该题的 Funny 生成。

- Prompt 中必须强调：
  - 不得改写输入中的任何公式或物理符号。
  - 不要重复题干与答案，只需输出解释与记忆辅助信息。
  - 只输出一个 JSON 对象，不要在前后添加自然语言注释。

## Markdown 渲染约束（markdown_renderer.py）

职责：接收 EMQuestion + LLM 输出 dict，返回完整的 Obsidian Markdown 字符串，不负责写文件。
约束与建议：
- 题干与解析：
  - 从 JSON 原样插入 question_raw 与 analysis_official，其中 LaTeX 表达式保持不变。
- 图片：
  - 针对 images_paths 中的每个条目生成图像引用。由于主脚本会将资源同步至 Vault 内部的 assets 文件夹，引用路径应相对于该题卡在 Vault 中的位置。例如：
    ![](../../assets/em_diagrams/) （假设题卡在二级目录下）
- Funny 区域 Callout：
  - 使用格式：
    > [!tip] Funny Tutor
    后续内容纳入 funny_explanation 和 memory_aids。
- 翻车点区域 Callout：
  - 使用格式：
    > [!warning] 翻车点
    后续列出 common_misconceptions 中的条目。
- 知识树与标签：
  - 利用 knowledge_tree_path 和 knowledge_main：
    - 在文末或文首添加若干 [[节点名]] 双链。
    - 按约定规则生成标签，例如 #高中物理/电磁学、#真题/选择题。

## 电磁学知识树（固定版本）

为统一 knowledge_tree_path 与 Vault 目录结构，MVP 固定以下高二电磁学知识树（2–3 层）：

- 一级：磁与电磁感应
  - 二级：磁场基础
    - 三级：磁感应强度与磁感线
    - 三级：通电直导线与线圈的磁场
    - 三级：带电粒子在匀强磁场中的运动
  - 二级：电磁感应
    - 三级：感应电动势与法拉第定律
    - 三级：楞次定律与方向判断
    - 三级：典型装置（滑线、线圈切割磁感线）

- 一级：交变电流与电磁波
  - 二级：交变电流
    - 三级：正弦交流的物理量（有效值、峰值、频率）
    - 三级：RLC 串联电路与电压电流关系
  - 二级：电磁波
    - 三级：电磁波的产生与传播
    - 三级：无线电通信基础（调幅、调频的物理本质）

knowledge_tree_path 字段示例：
["磁与电磁感应", "电磁感应", "感应电动势与法拉第定律"]

生成题卡时，generate_vault.py 应基于 knowledge_tree_path 调用 os.makedirs(..., exist_ok=True) 创建相应目录。

## 抽题策略（daily_index.py）

MVP 抽题策略：简单随机且当次不重复。
- 输入：全部题目 ID 列表；每日抽题数量 daily_count（由 config.toml 配置）。
- 输出：一个列表，长度为 min(daily_count, 题目总数)，元素互不重复。
- 逻辑约定：
  - 当 daily_count 超过题目总数时，返回全部题目，不报错。
  - 不调用 LLM，仅依赖题库和已有题卡文件列表。
## Testing Strategy

- 单元测试（pytest）：
  1. Schema 校验（test_schema.py）
     - 构造合法与不合法 JSON 片段，验证合法数据被成功解析，不合法数据抛出清晰异常。
  2. Markdown 渲染（test_renderer.py）
     - 断言生成的 Markdown 字符串包含 Callout 标题行、双链字符串及图像引用字符串。
  3. LLM 解析逻辑（test_llm_client.py）
     - 使用 mock 响应验证无论是纯 JSON 还是带代码块外壳的 JSON 都能被稳定解析。
  4. 抽题逻辑（test_daily_index.py）
     - 验证抽取的题目数量正确且无重复。

- Lint 与格式：
  - 使用 ruff 对 src 与 tests 做静态检查和基本自动修复。

- 手工集成验证：
  - 使用仅含 3–5 题的迷你 questions_em.json 运行生成。
  - 用 Obsidian 打开 Vault 检查看板双链、LaTeX 渲染及图片加载是否正常。

## Boundaries

- Always：
  - 在处理题库前必须使用 Pydantic 校验 JSON。
  - 写入 Markdown 时，所有 LaTeX 公式与物理专有名词必须直接来自 JSON，不经 LLM 修改。
  - 执行 generate_vault.py 时，必须将 data/assets/ 的内容同步到 vault/FunnyTutor_EM_Vault/assets/，以保证 Obsidian 沙盒内可访问图片。
  - 对每道题，在决定是否调用 LLM 之前须检查对应 Markdown 题卡是否存在。若存在且未指定 --force，跳过该题 LLM 调用。
  - 所有 LLM 解析失败应仅跳过当前题目，并记录日志，不阻断整体流程。

- Ask first：
  - 修改 questions_em.json 中核心字段的结构或语义。
  - 引入新的模板引擎（如 jinja2）或更改 LLM 客户端底层实现。
  - 大幅调整 Vault 根目录或知识树目录命名规则。

- Never：
  - 不在代码库或 Prompt 中硬编码 API Key。
  - 不让 LLM 承担大题的数值计算或逻辑推导；定量结论以 analysis_official 为准。
  - 不依赖任何必须的第三方 Obsidian 插件。

## Success Criteria

1. Schema 完备与验证通过：模型能够成功校验包含 10–20 题的 questions_em.json，无结构性错误。
2. 端到端增量生成稳定：初次运行生成全量卡片和主页；新增题目后再次运行，旧题跳过调用，新题触发调用并更新主页。
3. 资产沙盒隔离兼容：图片正确从项目源目录复制至 Vault 内，相对路径引用在 Obsidian 中正常渲染。
4. LLM 响应解析鲁棒：无论 JSON 是否包裹了代码块语法，解析器均不抛出 JSONDecodeError。
5. 测试与 Lint 全部通过：pytest 全部通过，ruff check 无阻塞级错误。

## Open Questions

1. 如果同一道真题在源 JSON 中更新了 `analysis_official` 字段的内容，当前的“检测文件是否存在即跳过”的简单增量构建策略是否足够？未来是否需要引入文件 Hash 比对机制来触发更新？（MVP 阶段暂维持简单判断，后续迭代考虑加入 hash 校验）。
2. `knowledge_tree_path` 层级改变时，是否需要脚本提供自动清理 Obsidian 内部旧目录（孤儿文件）的机制？（MVP 阶段由人工在 Obsidian 内删除旧文件解决）。