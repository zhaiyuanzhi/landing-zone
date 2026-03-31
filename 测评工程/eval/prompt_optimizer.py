"""
提示词优化器

使用 claude-opus-4-6 + 自适应思考，基于多测试用例的评测结果，
针对性地修改系统提示词，重点提升得分最低的维度。
"""

import re
import anthropic

from eval_config import ANTHROPIC_API_KEY, OPTIMIZER_MODEL
from eval_rubric import RUBRIC
from evaluator import aggregate_eval_results


# ============================================================
# 核心优化函数
# ============================================================

def optimize_prompt(
    current_prompt: str,
    eval_results: list[dict],
    iteration: int,
) -> dict:
    """
    基于多条评测结果生成优化后的系统提示词。

    Args:
        current_prompt: 当前系统提示词
        eval_results:   evaluate_response() 返回值列表（含 query 字段）
        iteration:      当前迭代轮次（用于日志标注）

    Returns:
        {
            "optimized_prompt":      str,  # 完整的新版提示词
            "changes_summary":       str,  # 改动要点列表
            "expected_improvements": str,  # 预期改善描述
        }
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    agg = aggregate_eval_results(eval_results)
    eval_detail_str = _format_eval_detail(eval_results)

    # 最差的 3 个维度
    worst_dims_str = "\n".join(
        f"  - {RUBRIC[d]['name']}: {s:.1f}/10（权重 {int(RUBRIC[d]['weight']*100)}%）"
        for d, s in agg.get("worst_dimensions", [])
    )

    # 所有维度均分
    all_scores_str = "\n".join(
        f"  - {RUBRIC[d]['name']}: {s:.1f}/10"
        for d, s in agg.get("avg_scores", {}).items()
    )

    optimizer_system = (
        "你是一位顶级提示词工程师，专注于优化金融/市场分析 LLM 系统提示词。\n"
        "你深知：好的提示词能引导模型产生特定行为，而不是简单地堆砌要求。\n"
        "你的改动必须精准、可验证，每一处修改都能直接影响模型输出行为。"
    )

    optimizer_user = f"""# 任务：优化市场分析智能体系统提示词（第 {iteration} 轮 → 第 {iteration + 1} 轮）

---

## 当前系统提示词
```
{current_prompt}
```

---

## 本轮评测摘要（{len(eval_results)} 个测试用例）

### 各维度平均分
{all_scores_str}

### 最需改进的 3 个维度
{worst_dims_str}

### 详细评测反馈（含提示词缺陷分析）
{eval_detail_str}

---

## 优化原则
1. **针对性修复**：重点解决得分最低维度对应的提示词缺陷
2. **保留优势**：不破坏得分较高维度的有效指令
3. **行为驱动**：每个改动须能直接改变模型的输出行为（而非仅增加文字描述）
4. **精简优先**：避免提示词无限膨胀，相同效果下优先用更少的文字表达
5. **可测试性**：每个改动都应能被后续评测验证

---

## 输出格式

请严格按以下 XML 标签输出，不要添加其他内容：

<optimized_prompt>
[完整的优化后系统提示词，保持 Markdown 格式，不要截断]
</optimized_prompt>

<changes_summary>
[用要点列表（- 改动内容：改动原因）说明你做了哪些修改，每条不超过 2 句话]
</changes_summary>

<expected_improvements>
[预期每个改动会在哪个评分维度带来多少分的提升，格式：维度名：预期从 X 分提升至 Y 分，原因]
</expected_improvements>
"""

    response = client.messages.create(
        model=OPTIMIZER_MODEL,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=optimizer_system,
        messages=[{"role": "user", "content": optimizer_user}],
    )

    full_text = "".join(
        b.text for b in response.content if b.type == "text"
    )

    return {
        "optimized_prompt":      _extract_tag(full_text, "optimized_prompt"),
        "changes_summary":       _extract_tag(full_text, "changes_summary"),
        "expected_improvements": _extract_tag(full_text, "expected_improvements"),
        "raw_response":          full_text,  # 保留完整输出便于调试
    }


# ============================================================
# 内部工具函数
# ============================================================

def _extract_tag(text: str, tag: str) -> str:
    """提取 XML 标签内的内容，并去除首尾空白"""
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _format_eval_detail(eval_results: list[dict]) -> str:
    """将评测结果列表格式化为供 LLM 阅读的文本"""
    lines = []
    for i, r in enumerate(eval_results, 1):
        lines.append(f"### 测试用例 {i}")
        lines.append(f"**查询**: {r.get('query', 'N/A')}")
        lines.append(f"**加权总分**: {r['weighted_score']:.1f}/10\n")
        lines.append("**各维度评分与反馈**:")
        for dim, fb in r["feedback"].items():
            lines.append(
                f"- **{fb['name']}** ({fb['score']:.1f}分)  \n"
                f"  理由: {fb['reason']}  \n"
                f"  改进建议: {fb['improvement']}"
            )
        lines.append(f"\n**提示词缺陷分析**: {r['prompt_weakness']}")
        lines.append("")
    return "\n".join(lines)
