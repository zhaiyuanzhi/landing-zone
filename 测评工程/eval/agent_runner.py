"""
市场分析智能体调用模块

通过 OpenAI 兼容接口调用 qwen3-235b-a22b-instruct-2507，
将市场上下文数据注入 user 消息，system 消息使用当前（或传入的）系统提示词。
"""

import sys
import os
import json

# 将项目根目录加入路径，以便导入 market_context
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from market_context import build_market_context, SYSTEM_PROMPT as DEFAULT_SYSTEM_PROMPT
from eval_config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL


def run_market_agent(
    query: str,
    system_prompt: str | None = None,
    markets: list | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> dict:
    """
    调用市场分析智能体，返回完整回复及元数据。

    Args:
        query:         用户查询文本
        system_prompt: 可选，覆盖默认系统提示词（用于测试迭代版本）
        markets:       要包含的市场列表，默认全部
        max_tokens:    最大输出 token 数
        temperature:   生成温度

    Returns:
        {
            "response":           str,   # 智能体回复文本
            "prompt_tokens":      int,   # 输入 token 数
            "completion_tokens":  int,   # 输出 token 数
            "model":              str,   # 实际使用的模型
            "error":              str | None,
        }
    """
    client = OpenAI(
        api_key=QWEN_API_KEY,
        base_url=QWEN_BASE_URL,
    )

    # 组装市场上下文
    ctx = build_market_context(
        markets=markets,
        include_macro=True,
        include_sentiment=True,
        include_events=True,
    )
    market_data_str = json.dumps(ctx["data"], ensure_ascii=False, indent=2)

    effective_system = system_prompt or DEFAULT_SYSTEM_PROMPT

    # 将数据与查询拼入 user 消息，避免污染 system prompt 缓存
    user_message = (
        f"## 当前市场数据快照（时间：{ctx['snapshot_time']}）\n\n"
        f"```json\n{market_data_str}\n```\n\n"
        f"## 用户查询\n\n{query}"
    )

    try:
        resp = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": effective_system},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return {
            "response":          resp.choices[0].message.content or "",
            "prompt_tokens":     resp.usage.prompt_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            "model":             resp.model,
            "error":             None,
        }
    except Exception as exc:
        return {
            "response":          "",
            "prompt_tokens":     0,
            "completion_tokens": 0,
            "model":             QWEN_MODEL,
            "error":             str(exc),
        }
