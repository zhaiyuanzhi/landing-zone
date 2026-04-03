"""
Claude 单模型评测器

使用 claude-opus-4-6 + 自适应思考 + JSON Schema 结构化输出，
对市场分析智能体的回复进行 7 维度评分。
"""

import json
import anthropic
from pydantic import BaseModel, Field

from eval_rubric import RUBRIC, format_rubric_for_prompt, calculate_weighted_score


# ============================================================
# 共享 Pydantic 输出模型（供其他评测器模块复用）
# ============================================================

class DimensionScore(BaseModel):
    score: float = Field(ge=1.0, le=10.0, description="得分 1–10（可用 0.5 步长）")
    reason: str  = Field(description="得分理由：2–3 句，须引用回复中的具体内容")
    improvement: str = Field(description="针对本维度的具体改进建议")


class EvaluationResult(BaseModel):
    structure_completeness: DimensionScore
    data_accuracy:          DimensionScore
    analysis_depth:         DimensionScore
    conclusion_clarity:     DimensionScore
    actionability:          DimensionScore
    professionalism:        DimensionScore
    risk_disclosure:        DimensionScore
    overall_comment: str = Field(description="整体评语 3–5 句，指出最大优势和最需改进的方面")
    prompt_weakness: str = Field(description="从提示词设计角度分析质量不足的原因，给出 2–3 条改写建议")


# ============================================================
# 评测函数
# ============================================================

EVAL_SYSTEM = (
    "你是一位严格、客观的市场分析报告质量评审专家，专注于评测 AI 市场分析智能体的回复质量。\n"
    "你的评分必须基于证据，不给面子分，低质量回复须给低分。\n"
    "每条评分理由都要引用回复中的具体内容（句子或数据）。"
)


def build_eval_prompt(
    query: str,
    agent_response: str,
    system_prompt: str,
    iteration: int,
    data_context: str = "",
) -> str:
    """构建适用于所有评测器的通用评测提示词"""
    rubric_text = format_rubric_for_prompt()

    data_section = ""
    if data_context:
        data_section = f"""
## 提供给模型的市场数据（用于核查 data_accuracy 维度）
```
{data_context}
```
"""

    return f"""{rubric_text}

---

# 待评测内容（第 {iteration} 轮）

## 用户查询
{query}

## 系统提示词（供提示词缺陷分析使用）
```
{system_prompt}
```
{data_section}
## 智能体回复
```
{agent_response}
```

---

# 评分要求
- 每个维度给出 1–10 分（可用 0.5 步长），严格依照评分标准
- reason 须引用回复中的具体内容或数据
- data_accuracy 维度须对照上方市场数据核查智能体引用的数据是否准确
- improvement 需对提示词工程有实际指导意义
- prompt_weakness 仅分析提示词设计问题，不评价数据质量本身
"""


def parse_eval_result(result: EvaluationResult) -> dict:
    """将 EvaluationResult Pydantic 对象转为标准评测结果字典"""
    scores, feedback = {}, {}
    for dim in RUBRIC:
        ds: DimensionScore = getattr(result, dim)
        scores[dim] = ds.score
        feedback[dim] = {
            "name":        RUBRIC[dim]["name"],
            "score":       ds.score,
            "reason":      ds.reason,
            "improvement": ds.improvement,
        }
    return {
        "scores":          scores,
        "weighted_score":  calculate_weighted_score(scores),
        "feedback":        feedback,
        "overall_comment": result.overall_comment,
        "prompt_weakness": result.prompt_weakness,
    }


def evaluate_with_claude(
    query: str,
    agent_response: str,
    system_prompt: str,
    iteration: int,
    api_key: str,
    model: str = "claude-opus-4-6",
    data_context: str = "",
) -> dict:
    """
    使用 Claude 进行评测，返回标准评测结果字典。

    Returns:
        标准评测结果，含 scores / weighted_score / feedback /
        overall_comment / prompt_weakness
    Raises:
        任何 Anthropic API 异常
    """
    client = anthropic.Anthropic(api_key=api_key)
    eval_user = build_eval_prompt(query, agent_response, system_prompt, iteration, data_context)
    schema = EvaluationResult.model_json_schema()

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=EVAL_SYSTEM,
        messages=[{"role": "user", "content": eval_user}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )

    text = next((b.text for b in response.content if b.type == "text"), "{}")
    result = EvaluationResult.model_validate(json.loads(text))
    return parse_eval_result(result)
