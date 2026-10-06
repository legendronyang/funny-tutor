#!/usr/bin/env python3
# InfraMind Orchestrator - Native Gemini CLI Adapter
# File: utils/llm_client.py
#
# [1] 基础文本生成示例
# ##############################################################################
# client = LLMClient()
# reply = client.generate("解释什么是 Pod？", system_instruction="简明扼要。")
#
# [2] 结构化输出示例与 Markdown 剥离
# ##############################################################################
# import json, re
# raw_response = client.generate("分析日志", "输出JSON")
# m_prefix = r"^" + r"```" + r"json\s*"
# m_suffix = r"```" + r"$"
# clean_json = re.sub(m_prefix, "", raw_response, flags=re.MULTILINE)
# clean_json = re.sub(m_suffix, "", clean_json, flags=re.MULTILINE).strip()
# data = json.loads(clean_json)

import os
import sys
import yaml
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List

# ##############################################################################
# ⚙️ 全局配置区 (GLOBAL CONFIGURATIONS)
# ##############################################################################

# 鉴权优先级 1: API Key (适用于 Google AI Studio)
# 专家建议：通过环境变量注入，不要在此处写明文，防泄露。
DEFAULT_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 鉴权优先级 2: GCP Project (适用于 Vertex AI)
# 当 API Key 为空时，作为回退鉴权机制。
DEFAULT_GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "gcp-hps-ai-development-01")

CONFIG_YAML_REL_PATH = "config/models.yaml"
SANDBOX_DIR_NAME = "input"

DEFAULT_MODEL_CASCADE = [
    "gemini-2.5-pro",         # [首选] 拦截至本地 Qwen 9B
    "gemini-3.5-flash",       # [备选 1] 拦截至本地 Qwen 9B
    "gemini-3.5-flash-lite",  # [备选 2] 拦截至本地 Qwen 9B
    "gemini-3.1-pro-preview", # [备选 3] 拦截至本地 Qwen 9B
    "gemini-3.8-flash"        # [兜底] 放行至云端 Real Gemini Cloud API
]

FATAL_ERROR_KEYWORDS = [
    "unauthorized", "authentication failed", 
    "invalid credentials", "login required", "no token",
    "api key not valid", "api key expired", "invalid api key"
]

CASCADE_TRIGGER_KEYWORDS = [
    "quota exceeded", "rate limit", "resource exhausted",
    "429", "daily limit", "503", "service unavailable"
]

# ##############################################################################
# 🛠️ 核心客户端实现
# ##############################################################################
class LLMClient:
    def __init__(self, model_name: Optional[str] = None):
        self.gemini_bin = self._resolve_gemini_binary()
        self.model_cascade = self._load_model_cascade(model_name)
        self.model_name = self.model_cascade[0]

    def _load_model_cascade(self, requested_model: Optional[str] = None) -> List[str]:
        yaml_cascade = []
        base_dir = Path(__file__).resolve().parent.parent
        config_yaml = base_dir / CONFIG_YAML_REL_PATH

        if config_yaml.exists():
            try:
                with open(config_yaml, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                yaml_cascade = [
                    item["name"] for item in cfg.get("active_cascade", [])
                    if isinstance(item, dict) and "name" in item
                ]
            except Exception as e:
                print(f"[警告] 读取配置失败: {e}，使用默认降级链。", file=sys.stderr)

        cascade = yaml_cascade if yaml_cascade else DEFAULT_MODEL_CASCADE
        start_model = requested_model or os.environ.get("VLM_MODEL")
        
        if start_model:
            return [start_model] + [m for m in cascade if m != start_model]
        return cascade

    def _resolve_gemini_binary(self) -> str:
        bin_path = shutil.which("gemini")
        if bin_path:
            return bin_path

        nvm_dir = Path.home() / ".nvm" / "versions" / "node"
        if nvm_dir.exists():
            for node_dir in sorted(nvm_dir.glob("*"), reverse=True):
                candidate = node_dir / "bin" / "gemini"
                if candidate.exists() and os.access(candidate, os.X_OK):
                    return str(candidate)
        return "gemini"

    def _categorize_error(self, error_text: str) -> str:
        lowered = error_text.lower()
        if any(kw in lowered for kw in FATAL_ERROR_KEYWORDS):
            return 'FATAL'
        if any(kw in lowered for kw in CASCADE_TRIGGER_KEYWORDS):
            return 'RETRY'
        return 'UNKNOWN'

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        full_prompt = ""
        if system_instruction:
            full_prompt += f"[SYSTEM INSTRUCTION]\n{system_instruction}\n\n"
        full_prompt += f"[USER REQUEST]\n{prompt}"

        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"
        
        # 智能鉴权路由：优先使用 API Key，否则使用 GCP Project
        if DEFAULT_GEMINI_API_KEY:
            env["GEMINI_API_KEY"] = DEFAULT_GEMINI_API_KEY
            # 移除 GCP 配置以防止 CLI 工具混淆鉴权链路
            env.pop("GOOGLE_CLOUD_PROJECT", None)
        else:
            env["GOOGLE_CLOUD_PROJECT"] = DEFAULT_GCP_PROJECT

        last_error = None

        for active_model in self.model_cascade:
            cmd = [
                self.gemini_bin,
                "--model", active_model,
                "--skip-trust",
                "-y",
                "-p", full_prompt
            ]

            try:
                process = subprocess.run(
                    cmd, capture_output=True, text=True,
                    env=env, timeout=180, check=True
                )
                output = process.stdout.strip()
                if output:
                    return output
                raise RuntimeError("CLI 返回空字符串")

            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError) as e:
                err_stdout = getattr(e, 'stdout', '') or ''
                err_stderr = getattr(e, 'stderr', '') or ''
                err_text = f"{err_stdout} {err_stderr}".strip() or str(e)
                last_error = err_text

                err_type = self._categorize_error(err_text)
                
                if err_type == 'FATAL':
                    print(f"[致命错误] 鉴权失败 (API Key无效或凭证错误)。模型 [{active_model}]", file=sys.stderr)
                    raise RuntimeError(f"Fatal auth error: {err_text}") from e
                
                elif err_type == 'RETRY' or isinstance(e, subprocess.TimeoutExpired):
                    print(f"[模型降级] [{active_model}] 受限/超时，尝试降级...", file=sys.stderr)
                    continue 
                else:
                    print(f"[未知错误] [{active_model}] 发生未知错误，尝试降级...", file=sys.stderr)
                    continue

        raise RuntimeError(f"所有模型降级尝试均失败。最后错误: {last_error}")

    def analyze_image(self, image_path: Path, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not image_path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        abs_p = image_path.resolve()
        cwd_p = Path.cwd().resolve()

        try:
            abs_p.relative_to(cwd_p)
            target_img_path = abs_p
        except ValueError:
            local_input = cwd_p / SANDBOX_DIR_NAME
            local_input.mkdir(exist_ok=True)
            target_img_path = local_input / abs_p.name
            shutil.copy2(abs_p, target_img_path)

        vlm_user_prompt = (
            f"请使用 ReadFile 工具读取图片 `{target_img_path.relative_to(cwd_p)}` 的像素内容。\n\n{prompt}"
        )
        return self.generate(vlm_user_prompt, system_instruction=system_instruction)


if __name__ == "__main__":
    print("正在自检连通性...")
    client = LLMClient()
    auth_mode = "API Key (AI Studio)" if DEFAULT_GEMINI_API_KEY else "GCP Project (Vertex AI)"
    print(f"├─ 当前鉴权链路 : {auth_mode}")
    print(f"├─ 降级链(Cascade) : {client.model_cascade}")
    try:
        reply = client.generate("Please output exactly one word: OK.")
        print(f"└─ 回复: {reply}")
        print("验证通过！")
    except Exception as e:
        print(f"验证失败: {ge}")
