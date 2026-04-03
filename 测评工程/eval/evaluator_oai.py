"""
通用 OpenAI 兼容评测器

支持以下服务商（均使用 OpenAI SDK + 自定义 base_url）：
  - 豆包 (Doubao)   doubao-seed-2-0-pro-260215   火山引擎 ark
  - DeepSeek        deepseek-reasoner / deepseek-chat
  - 阿里千问 (Qwen)  qwen-max / qwen-plus 等

各模型差异处理：
  - DeepSeek-R1 (deepseek-reasoner): 响应体含 reasoning_content 字段，
    实际 JSON 在 content 字段；此外可能以 <think>...</think> 标签包裹推理过程
  - 其余模型: 直接使用 response_format={"type": "json_object"} 强制 JSON 输出
"""

import json
import re
from openai import OpenAI

from eval_rubric import RUBRIC, calculate_weighted_score
from evaluator_claude import (
    DimensionScore,
    EvaluationResult,
    build_eval_prompt,
    parse_eval_result,
    EVAL_SYSTEM,
)


# ============================================================
# JSON 输出提示词模板
# ============================================================

_JSON_SCHEMA_HINT = """
请严格按以下 JSON 格式输出评测结果，不要输出任何其他内容（无注释、无 markdown 代码块）：

{
  "structure_completeness": {"score": <1-10的数值>, "reason": "<2-3句理由，引用原文>", "improvement": "<改进建议>"},
  "data_accuracy":          {"score": <1-10的数值>, "reason": "<2-3句理由，引用原文>", "improvement": "<改进建议>"},
  "analysis_depth":         {"score": <1-10的数值>, "reason": "<2-3句理由，引用原文>", "improvement": "<改进建议>"},
  "conclusion_clarity":     {"score": <1-10的数值>, "reason": "<2-3句理由，引用原文>", "improvement": "<改进建议>"},
  "actionability":          {"score": <1-10的数值>, "reason": "<2-3句理由，引用原文>", "improvement": "<改进建议>"},
  "professionalism":        {"score": <1-10的数值>, "reason": "<2-3句理由，引用原文>", "improvement": "<改进建议>"},
  "risk_disclosure":        {"score": <1-10的数值>, "reason": "<2-3句理由，引用原文>", "improvement": "<改进建议>"},
  "overall_comment":        "<3-5句整体评语，指出最大优势和最需改进的方面>",
  "prompt_weakness":        "<从系统提示词设计角度分析质量不足的原因，给出2-3条改写建议>"
}
"""


# ============================================================
# JSON 提取工具
# ============================================================

def _extract_json(text: str) -> dict:
    """
    从模型输出文本中提取 JSON 对象。
    依次尝试：直接解析 → 代码块提取 → 花括号范围扫描
    """
    # 1. 去除 DeepSeek-R1 的 <think>...</think> 推理块
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. 从 ```json ... ``` 代码块中提取
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 4. 扫描最外层 { ... } 范围
    start = text.find("{")
    if start != -1:
        depth, end = 0, -1
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end != -1:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

    raise ValueError(f"无法从模型输出中提取有效 JSON，原始内容前 500 字：\n{text[:500]}")


def _raw_to_eval_result(raw: dict) -> dict:
    """将原始 JSON 字典转为标准评测结果，复用 Pydantic 验证"""
    result = EvaluationResult.model_validate(raw)
    return parse_eval_result(result)


# ============================================================
# 核心评测函数
# ============================================================

def evaluate_with_oai_compat(
    query: str,
    agent_response: str,
    system_prompt: str,
    iteration: int,
    api_key: str,
    base_url: str,
    model: str,
    use_json_mode: bool = True,
    timeout: float = 180.0,
    data_context: str = "",
) -> dict:
    """
    使用 OpenAI 兼容 API 进行评测。

    Args:
        query:          用户原始查询
        agent_response: 智能体回复
        system_prompt:  当前系统提示词
        iteration:      迭代轮次
        api_key:        服务商 API Key
        base_url:       服务商 OpenAI 兼容接口地址
        model:          模型名称
        use_json_mode:  是否使用 response_format=json_object
                        (DeepSeek-R1 不支持，需设为 False)

    Returns:
        标准评测结果字典（与 evaluate_with_claude 格式相同）
    """
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    # 拼接评测提示词，末尾追加 JSON 格式要求
    eval_user = build_eval_prompt(query, agent_response, system_prompt, iteration, data_context)
    eval_user += _JSON_SCHEMA_HINT

    kwargs = dict(
        model=model,
        max_tokens=4096,
        temperature=0.1,      # 低温度提高 JSON 格式稳定性
        messages=[
            {"role": "system", "content": EVAL_SYSTEM},
            {"role": "user",   "content": eval_user},
        ],
    )

    # 仅在支持 json_object 的模型上启用
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content or ""

    # DeepSeek-R1 的推理内容在 reasoning_content 字段，实际回复在 content
    # openai SDK 会将其透传，无需额外处理，_extract_json 已处理 <think> 标签
    raw = _extract_json(content)
    return _raw_to_eval_result(raw)
