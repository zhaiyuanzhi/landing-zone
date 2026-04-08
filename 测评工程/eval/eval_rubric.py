"""
市场分析智能体 —— 多维度评分标准 (Rubric)

7 个评分维度，各维度 1–10 分，加权求和得出最终分数。
权重配置见 eval_config.DIMENSION_WEIGHTS。
"""

from eval_config import DIMENSION_WEIGHTS

# ============================================================
# 评分标准定义
# ============================================================

RUBRIC: dict[str, dict] = {
    "structure_completeness": {
        "name": "结构完整性",
        "weight": DIMENSION_WEIGHTS["structure_completeness"],
        "description": "响应是否包含系统提示词要求的全部 7 个分析模块，且每个模块内容完整",
        "key_modules": [
            "核心结论（含置信度）",
            "宏观背景",
            "资本市场结构分析",
            "货币信用传导",
            "制度政策环境",
            "催化剂与风险（含具体日期）",
            "操作建议（含表格：方向/占比/时间/行业）",
        ],
        "criteria": {
            "1–3": "缺失 3 个及以上模块，或多个模块严重空洞（仅有标题无内容）",
            "4–6": "包含 5–6 个模块，或部分模块内容过于简略（不足 1 句实质分析）",
            "7–8": "包含全部 7 个模块，内容基本完整，少数模块稍显简略",
            "9–10": "全部 7 个模块均充实完整，结构清晰，子项要素齐备",
        },
    },

    "data_accuracy": {
        "name": "数据引用准确性",
        "weight": DIMENSION_WEIGHTS["data_accuracy"],
        "description": "引用的数字、指标、板块名称是否与上下文提供的市场数据完全一致，无捏造、无错误",
        "criteria": {
            "1–3": "存在明显数据错误（如指数点位相差 5%+）或大量捏造未提供的数据",
            "4–6": "部分数据引用不准确，或对未提供数据进行了无依据的推断",
            "7–8": "数据引用基本准确，偶有轻微误差或合理近似",
            "9–10": "所有关键数据引用精确，与提供数据完全吻合",
        },
    },

    "analysis_depth": {
        "name": "分析深度",
        "weight": DIMENSION_WEIGHTS["analysis_depth"],
        "description": "分析是否超越数据复述，提供逻辑推断、因果链条和前瞻性判断",
        "criteria": {
            "1–3": "仅罗列数据，无实质性分析或推断",
            "4–6": "有基本分析，但逻辑链条不完整，仅描述现象未挖掘原因",
            "7–8": "分析较为深入，逻辑清晰，有因果推断和短期前瞻",
            "9–10": "分析极为深入，宏观-中观-微观贯通，因果链完整，具备独立判断和前瞻观点",
        },
    },

    "conclusion_clarity": {
        "name": "结论明确性",
        "weight": DIMENSION_WEIGHTS["conclusion_clarity"],
        "description": "核心结论是否在 3 句话以内明确给出多/空/震荡判断并标注置信度",
        "criteria": {
            "1–3": "结论模糊，无明确方向判断，或观点矛盾自相抵消",
            "4–6": "有方向判断但置信度表述缺失或不规范（未使用高/中/低）",
            "7–8": "明确给出方向+置信度，但核心理由稍显冗长",
            "9–10": "≤3 句话内完整表达：方向 + 置信度（高/中/低）+ 核心依据",
        },
    },

    "actionability": {
        "name": "操作可行性",
        "weight": DIMENSION_WEIGHTS["actionability"],
        "description": "操作建议是否包含方向、仓位比例、时间窗口、重点板块、规避板块五要素",
        "criteria": {
            "1–3": "无实质性操作建议，或建议极度模糊（如：谨慎操作、视情况而定）",
            "4–6": "有操作建议但缺失关键要素（如无仓位比例或无时间窗口）",
            "7–8": "操作建议包含主要要素（4/5），基本可执行",
            "9–10": "五要素齐备（方向/仓位/时间/重点板块/规避板块），高度可执行",
        },
    },

    "professionalism": {
        "name": "专业性",
        "weight": DIMENSION_WEIGHTS["professionalism"],
        "description": "语言是否专业准确，事实与判断区分清晰，适合机构投资者晨会/研报场景",
        "criteria": {
            "1–3": "语言不专业，混淆事实与判断，或出现口语化表达",
            "4–6": "基本专业，但部分措辞不够准确，事实判断偶有混淆",
            "7–8": "专业性较强，事实与判断区分良好，适合机构阅读",
            "9–10": "高度专业，术语准确，事实判断严格区分，完全适合晨会/研报",
        },
    },

    "risk_disclosure": {
        "name": "风险提示",
        "weight": DIMENSION_WEIGHTS["risk_disclosure"],
        "description": "风险提示是否具体到事件名称和日期，而非空泛表述",
        "criteria": {
            "1–3": "无风险提示，或仅有'市场有风险'等完全空洞的表述",
            "4–6": "有具体风险事件但缺少日期，或日期模糊（如'下周'）",
            "7–8": "风险事件较为具体，大部分附有日期",
            "9–10": "所有风险事件均有具体名称 + 明确日期，完全可追踪",
        },
    },
}


# ── 自定义维度覆盖（由 Dashboard 写入 eval_results/custom_dimensions.json）────
import json as _json
import pathlib as _pathlib
_custom_dims_file = _pathlib.Path("eval_results") / "custom_dimensions.json"
if _custom_dims_file.exists():
    try:
        _custom_dims = _json.loads(_custom_dims_file.read_text(encoding="utf-8"))
        _new_rubric: dict[str, dict] = {}
        for _d in _custom_dims:
            _key = _d["key"]
            if _key in RUBRIC:
                # 覆盖已有维度的可编辑字段，保留详细评分标准
                _entry = dict(RUBRIC[_key])
                _entry["name"]        = _d.get("name", _entry["name"])
                _entry["weight"]      = float(_d["weight"])
                _entry["description"] = _d.get("description") or _entry["description"]
                if _d.get("criteria"):           # 用户若自定义了评分细则则覆盖
                    _entry["criteria"] = _d["criteria"]
                if _d.get("key_modules"):        # 用户若自定义了模块列表则覆盖
                    _entry["key_modules"] = _d["key_modules"]
                _new_rubric[_key] = _entry
            else:
                # 新增自定义维度
                _new_rubric[_key] = {
                    "name":        _d.get("name", _key),
                    "weight":      float(_d["weight"]),
                    "description": _d.get("description", ""),
                    "key_modules": _d.get("key_modules") or [],
                    "criteria":    _d.get("criteria") or {
                        "1–3":  "表现很差",
                        "4–6":  "表现一般",
                        "7–8":  "表现良好",
                        "9–10": "表现优秀",
                    },
                }
        RUBRIC = _new_rubric
    except Exception as _err:
        import warnings as _warnings
        _warnings.warn(f"[eval_rubric] 加载自定义维度失败，使用默认评分标准: {_err}")

# ============================================================
# 工具函数
# ============================================================

def calculate_weighted_score(scores: dict[str, float]) -> float:
    """
    根据各维度得分和权重计算加权总分。

    Args:
        scores: {dimension_key: score_float} 字典

    Returns:
        加权总分（保留 2 位小数）
    """
    total, weight_sum = 0.0, 0.0
    for dim, score in scores.items():
        w = RUBRIC[dim]["weight"]
        total += score * w
        weight_sum += w
    return round(total / weight_sum, 2) if weight_sum > 0 else 0.0


def format_rubric_for_prompt() -> str:
    """将评分标准格式化为适合嵌入 LLM 提示词的可读文本"""
    lines = ["# 评分标准\n"]
    for key, dim in RUBRIC.items():
        lines.append(f"## {dim['name']}（权重 {int(dim['weight'] * 100)}%）")
        lines.append(f"**评分说明**: {dim['description']}\n")
        for range_str, desc in dim["criteria"].items():
            lines.append(f"- **{range_str} 分**: {desc}")
        if "key_modules" in dim:
            lines.append(f"\n*必须包含的模块*: {', '.join(dim['key_modules'])}")
        lines.append("")
    return "\n".join(lines)


def score_summary(scores: dict[str, float]) -> str:
    """生成简洁的得分摘要字符串，用于日志输出"""
    lines = []
    for dim, score in scores.items():
        bar = "█" * int(score) + "░" * (10 - int(score))
        lines.append(f"  {RUBRIC[dim]['name']:12s}  {bar}  {score:4.1f}/10")
    weighted = calculate_weighted_score(scores)
    lines.append(f"\n  {'加权总分':12s}  {'─' * 10}  {weighted:4.2f}/10")
    return "\n".join(lines)
