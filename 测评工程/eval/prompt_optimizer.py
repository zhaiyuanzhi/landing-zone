"""
提示词优化器

支持多种后端模型（通过 eval_config.OPTIMIZER_CONFIG 切换）：
  - Anthropic Claude（原生 SDK，支持 adaptive thinking）
  - OpenAI 兼容接口：Qwen3-235B（支持 enable_thinking）、DeepSeek-R1、Doubao 等

切换方法：修改 eval_config.py 中的 OPTIMIZER_CONFIG 字典。
"""

import os
import re

from eval_config import OPTIMIZER_CONFIG
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
            "optimized_prompt":      str,
            "changes_summary":       str,
            "expected_improvements": str,
            "raw_response":          str,
        }
    """
    agg = aggregate_eval_results(eval_results)

    worst_dims_str = "\n".join(
        f"  - {RUBRIC[d]['name']}: {s:.1f}/10（权重 {int(RUBRIC[d]['weight']*100)}%）"
        for d, s in agg.get("worst_dimensions", [])
    )
    all_scores_str = "\n".join(
        f"  - {RUBRIC[d]['name']}: {s:.1f}/10"
        for d, s in agg.get("avg_scores", {}).items()
    )

    system_msg = (
        "你是一位顶级提示词工程师，专注于优化金融/市场分析 LLM 系统提示词。\n"
        "你深知：好的提示词能引导模型产生特定行为，而不是简单地堆砌要求。\n"
        "你的改动必须精准、可验证，每一处修改都能直接影响模型输出行为。"
    )

    user_msg = f"""# 任务：优化市场分析智能体系统提示词（第 {iteration} 轮 → 第 {iteration + 1} 轮）

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
{_format_eval_detail(eval_results)}

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

    provider = OPTIMIZER_CONFIG.get("provider", "anthropic")
    if provider == "anthropic":
        full_text = _call_anthropic(system_msg, user_msg)
    else:
        full_text = _call_openai_compat(system_msg, user_msg)

    return {
        "optimized_prompt":      _extract_tag(full_text, "optimized_prompt"),
        "changes_summary":       _extract_tag(full_text, "changes_summary"),
        "expected_improvements": _extract_tag(full_text, "expected_improvements"),
        "raw_response":          full_text,
    }


# ============================================================
# 后端调用
# ============================================================

def _call_anthropic(system_msg: str, user_msg: str) -> str:
    """Anthropic 原生 SDK，支持 adaptive thinking。"""
    import anthropic

    api_key = os.environ.get(OPTIMIZER_CONFIG["api_key_env"], "")
    client = anthropic.Anthropic(api_key=api_key)

    kwargs: dict = {
        "model":    OPTIMIZER_CONFIG["model"],
        "max_tokens": OPTIMIZER_CONFIG.get("max_tokens", 8192),
        "system":   system_msg,
        "messages": [{"role": "user", "content": user_msg}],
    }
    if OPTIMIZER_CONFIG.get("enable_thinking"):
        kwargs["thinking"] = {"type": "adaptive"}

    response = client.messages.create(**kwargs)
    return "".join(b.text for b in response.content if b.type == "text")


def _call_openai_compat(system_msg: str, user_msg: str) -> str:
    """OpenAI 兼容接口（Qwen3、DeepSeek、Doubao 等）。"""
    from openai import OpenAI

    api_key  = os.environ.get(OPTIMIZER_CONFIG["api_key_env"], "")
    base_url = OPTIMIZER_CONFIG.get("base_url")
    model    = OPTIMIZER_CONFIG["model"]
    max_tok  = OPTIMIZER_CONFIG.get("max_tokens", 8192)

    client = OpenAI(api_key=api_key, base_url=base_url)

    create_kwargs: dict = {
        "model":      model,
        "max_tokens": max_tok,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
    }

    # Qwen3：通过 extra_body 启用思维链
    if OPTIMIZER_CONFIG.get("enable_thinking") and "qwen3" in model.lower():
        create_kwargs["extra_body"] = {"enable_thinking": True}

    resp = client.chat.completions.create(**create_kwargs)
    return resp.choices[0].message.content or ""


# ============================================================
# 内部工具函数
# ============================================================

def _extract_tag(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _format_eval_detail(eval_results: list[dict]) -> str:
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
