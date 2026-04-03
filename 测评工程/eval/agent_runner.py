"""
市场分析智能体调用模块

通过 OpenAI 兼容接口调用模型，将数据上下文与用户查询注入 user 消息。

消息结构：
  system  = DEMO_SYSTEM_PROMPT（任务目标、角色、约束条件）
  user    = DEMO_DATA_CONTEXT（全部数据区块）+ 用户查询

数据来源：市场分析-提示词模板.md（由 demo_market_context.py 加载分割）
"""

from openai import OpenAI

from demo_market_context import DEMO_DATA_CONTEXT, DEMO_SYSTEM_PROMPT
from eval_config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL


def _build_user_message(query: str) -> str:
    return f"{DEMO_DATA_CONTEXT}\n\n## 用户查询\n\n{query}"


def run_market_agent(
    query: str,
    system_prompt: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    timeout: float = 500.0,
) -> dict:
    """
    调用市场分析智能体，返回完整回复及元数据。

    Args:
        query:         用户查询文本
        system_prompt: 可选，覆盖默认系统提示词（用于测试迭代版本）
        max_tokens:    最大输出 token 数
        temperature:   生成温度

    Returns:
        {
            "response":           str,
            "prompt_tokens":      int,
            "completion_tokens":  int,
            "model":              str,
            "error":              str | None,
        }
    """
    client = OpenAI(
        api_key=QWEN_API_KEY,
        base_url=QWEN_BASE_URL,
        timeout=timeout,
    )

    effective_system = system_prompt or DEMO_SYSTEM_PROMPT
    user_message = _build_user_message(query)

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
