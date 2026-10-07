该项目是借助于 https://github.com/addyosmani/agent-skills、WSL Ubuntu 中的本地 Ollama/Qwen3.5:9b 以及云端大模型一起开发实现的。

| source file | status | used skill |
| ----------- | ------ | ---------- |
| idea.md | ready | idea-refine |
| spec.md | ready | spec-driven-development |
| tasks/plan.md | ready | planning-and-task-breakdown |
| tasks/todo.md | ready | planning-and-task-breakdown |
| utils/llm_client.py | reference only | 尚未作为 funny-tutor 代码验证 |

## LLM architecture

Funny Tutor 通过统一 LLM Client + LiteLLM 路由模型。开发阶段默认使用 WSL Ubuntu 中 Ollama 运行的 Qwen3.5:9b；完成本地调试后，可以切换 Gemini、ChatGPT 等云端模型，对题库内容进行独立验证。

题库中的字段采用“缺失则生成、已有则独立核实”的策略。多个模型的验证结果应作为独立 evidence 保存，而不是让后调用的模型覆盖前一个模型的结果。

data/questions_em.json 当前只是少量历年真题开发 fixture，不定义正式题库 Schema；正式题库由 src/schema.py 中的 canonical model 定义，未来可以接收 OCR、人工录入或其他来源的数据后进行映射和补全。

下一步按照 incremental-implementation Skill，从 Task 2 开始逐步实现，并在每个 task 完成后运行测试、lint 和必要的真实集成验证。
