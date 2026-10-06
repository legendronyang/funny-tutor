#!/usr/bin/env python3
import os
import json
from llm_client import LLMClient

def run_tests():
    # 确保测试环境强制走本地代理和本地 Key
    os.environ["GOOGLE_GEMINI_BASE_URL"] = "http://localhost:4000"
    os.environ["GEMINI_API_KEY"] = "sk-gemini-local-key"
    
    print("初始化 LLMClient...")
    client = LLMClient()
    print(f"当前生效模型链: {client.model_cascade}\n")

    # 测试 1：基础问答能力
    print("▶ 测试 1: 基础文本生成")
    reply1 = client.generate("用一句话解释什么是 Clos 网络拓扑？")
    print(f"回答:\n{reply1}\n{'-'*40}")

    # 测试 2：System Instruction 角色扮演
    print("▶ 测试 2: 系统指令 (System Instruction) 注入")
    reply2 = client.generate(
        prompt="请分析这行报错：kernel panic - not syncing: VFS: Unable to mount root fs",
        system_instruction="你是一个资深的 Linux 驱动与底层网络硬件工程师。请直接给出最可能的原因，不要超过30个字。"
    )
    print(f"回答:\n{reply2}\n{'-'*40}")

    # 测试 3：结构化 JSON 输出与剥离
    print("▶ 测试 3: 结构化输出解析")
    raw_json_reply = client.generate(
        prompt="提取信息：Tomahawk 6 的带宽是 51.2T，采用 5nm 工艺。",
        system_instruction="输出严格的 JSON 格式，包含 bandwidth 和 process 两个字段，不要任何其他废话。"
    )
    print(f"原始输出:\n{raw_json_reply}")
    
    # 简单的 Markdown 代码块清洗
    clean_json = raw_json_reply.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(clean_json)
        print(f"解析成功: {parsed}")
    except json.JSONDecodeError:
        print("JSON 解析失败，模型输出了非标准格式。")

if __name__ == "__main__":
    run_tests()
