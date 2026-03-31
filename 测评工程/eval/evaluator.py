"""
Claude 评测器

使用 claude-opus-4-6 + 自适应思考 + 结构化输出，
对市场分析智能体的回复进行 7 个维度的客观评分。
"""

import json
from pydantic import BaseModel, Field
import anthropic

from eval_config import ANTHROPIC_API_KEY, EVALUATOR_MODEL
from eval_rubric import RUBRIC, format_rubric_for_prompt, calculate_weighted_score


# ============================================================
# Pydantic 结构化输出模型
# ============================================================

class DimensionScore(BaseModel):
    score: float = Field(ge=1.0, le=10.0, description="得分 1–10（可用 0.5 步长）")
    reason: str  = Field(description="得分理由：2–3 句话，须引用回复中的具体内容")
    improvement: str = Field(description="针对本维度的具体改进建议（对提示词工程有指导意义）")


class EvaluationResult(BaseModel):
    structure_completeness: DimensionScore
    data_accuracy:          DimensionScore
    analysis_depth:         DimensionScore
    conclusion_clarity:     DimensionScore
    actionability:          DimensionScore
    professionalism:        DimensionScore
    risk_disclosure:        DimensionScore

    overall_comment:  str = Field(description="整体评语：3–5 句话，指出最大优势和最需改进的方面")
    prompt_weakness:  str = Field(
        description="提示词缺陷分析：从系统提示词设计角度（非数据问题）分析是什么导致了回复质量不足，"
                    "给出 2–3 条具体的提示词改写建议"
    )


# ============================================================
# 核心评测函数
# ============================================================

def evaluate_response(
    query: str,
    agent_response: str,
    system_prompt: str,
    iteration: int = 0,
) -> dict:
    """
    使用 Claude 对单条智能体回复进行多维度评分。

    Args:
        query:          用户原始查询
        agent_response: 智能体回复文本
        system_prompt:  本次使用的系统提示词（用于提示词缺陷分析）
        iteration:      当前迭代轮次（供日志标注使用）

    Returns:
        {
            "scores":          {dim: score},  # 各维度原始分
            "weighted_score":  float,         # 加权总分
            "feedback":        {dim: {...}},  # 各维度详细反馈
            "overall_comment": str,
            "prompt_weakness": str,
        }
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    rubric_text = format_rubric_for_prompt()

    eval_system = (
        "你是一位严格、客观的市场分析报告质量评审专家，专注于评测 AI 市场分析智能体的回复质量。\n"
        "你的评分必须基于证据，不给'面子分'，低质量回复须给低分。\n"
        "每条评分理由都要引用回复中的具体内容（句子或数据）。"
    )

    eval_user = f"""{rubric_text}

---

# 待评测内容（第 {iteration} 轮迭代）

## 用户查询
{query}

## 系统提示词（供提示词缺陷分析使用）
```
{system_prompt}
```

## 智能体回复
```
{agent_response}
```

---

# 评分要求
- 每个维度给出 1–10 分（可用 0.5 步长），严格依照评分标准
- reason 须引用回复中的具体内容或数据
- improvement 需对提示词工程有实际指导意义
- prompt_weakness 仅分析提示词设计问题，不评价数据质量本身
"""

    # 构建 JSON Schema（基于 Pydantic 模型）
    schema = EvaluationResult.model_json_schema()

    response = client.messages.create(
        model=EVALUATOR_MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=eval_system,
        messages=[{"role": "user", "content": eval_user}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )

    # 提取 text block 中的 JSON
    text_content = next(
        (b.text for b in response.content if b.type == "text"), "{}"
    )
    raw = json.loads(text_content)
    result = EvaluationResult.model_validate(raw)

    # 整理输出
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


# ============================================================
# 多测试用例汇总
# ============================================================

def aggregate_eval_results(eval_results: list[dict]) -> dict:
    """
    汇总多条评测结果，计算各维度均分和整体均分。

    Args:
        eval_results: evaluate_response() 的返回值列表

    Returns:
        {
            "avg_scores":         {dim: avg_score},
            "avg_weighted_score": float,
            "worst_dimensions":   [(dim, avg_score), ...],  # 得分最低的 3 个维度
        }
    """
    if not eval_results:
        return {}

    dims = list(eval_results[0]["scores"].keys())
    avg_scores = {
        d: round(sum(r["scores"][d] for r in eval_results) / len(eval_results), 2)
        for d in dims
    }
    avg_weighted = round(
        sum(r["weighted_score"] for r in eval_results) / len(eval_results), 2
    )
    worst = sorted(avg_scores.items(), key=lambda x: x[1])[:3]

    return {
        "avg_scores":         avg_scores,
        "avg_weighted_score": avg_weighted,
        "worst_dimensions":   worst,
    }
