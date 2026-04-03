"""
多模型集成评测器（Ensemble）

将多个评测器的分数通过加权平均合并，输出综合评测结果。

特性：
  - 自动跳过调用失败的评测器，仍能正常返回结果（至少 1 个成功即可）
  - 记录每个评测器的原始分，可在报告中对比"评测者之间的分歧"
  - 提供标准差字段，衡量各评测器对同一维度的一致性
"""

import math
import os
from typing import Callable

from eval_rubric import RUBRIC, calculate_weighted_score
from evaluator_claude import evaluate_with_claude
from evaluator_oai import evaluate_with_oai_compat


# ============================================================
# 评测器调度表
# ============================================================

def _build_evaluator_fn(cfg: dict) -> Callable:
    """
    根据配置字典返回一个统一签名的评测函数：
        fn(query, agent_response, system_prompt, iteration, data_context) -> dict
    """
    provider = cfg["provider"]
    api_key  = os.environ.get(cfg["api_key_env"], "")

    timeout = float(cfg.get("timeout", 180))

    if provider == "anthropic":
        def _claude_fn(query, agent_response, system_prompt, iteration, data_context=""):
            return evaluate_with_claude(
                query=query,
                agent_response=agent_response,
                system_prompt=system_prompt,
                iteration=iteration,
                api_key=api_key,
                model=cfg["model"],
                data_context=data_context,
            )
        return _claude_fn

    elif provider == "openai_compat":
        use_json_mode = cfg.get("use_json_mode", True)
        base_url      = cfg["base_url"]

        def _oai_fn(query, agent_response, system_prompt, iteration, data_context=""):
            return evaluate_with_oai_compat(
                query=query,
                agent_response=agent_response,
                system_prompt=system_prompt,
                iteration=iteration,
                api_key=api_key,
                base_url=base_url,
                model=cfg["model"],
                use_json_mode=use_json_mode,
                timeout=timeout,
                data_context=data_context,
            )
        return _oai_fn

    else:
        raise ValueError(f"未知 provider: {provider}")


# ============================================================
# 集成评测核心
# ============================================================

def evaluate_ensemble(
    query: str,
    agent_response: str,
    system_prompt: str,
    iteration: int,
    evaluator_configs: dict,
    data_context: str = "",
) -> dict:
    """
    使用所有已启用的评测器进行评测，返回加权集成结果。

    Args:
        query:             用户查询
        agent_response:    智能体回复
        system_prompt:     当前系统提示词
        iteration:         迭代轮次
        evaluator_configs: EVALUATOR_CONFIGS 字典（来自 eval_config）

    Returns:
        {
            "scores":           {dim: avg_score},   # 各维度集成分
            "weighted_score":   float,              # 集成加权总分
            "feedback":         {dim: {...}},        # 来自得分最高评测器的反馈
            "overall_comment":  str,                # 来自得分最高评测器
            "prompt_weakness":  str,                # 来自得分最高评测器
            "per_evaluator":    {name: result},     # 各评测器原始结果
            "evaluator_std":    {dim: std},         # 各维度跨评测器标准差
            "evaluators_used":  [name, ...],        # 成功的评测器列表
        }
    """
    enabled = {
        name: cfg
        for name, cfg in evaluator_configs.items()
        if cfg.get("enabled", False)
    }
    if not enabled:
        raise RuntimeError("没有启用任何评测器，请在 eval_config.EVALUATOR_CONFIGS 中设置 enabled=True")

    per_evaluator: dict[str, dict] = {}
    failures: dict[str, str] = {}

    # ── 依次调用各评测器 ───────────────────────────────────────
    for name, cfg in enabled.items():
        api_key = os.environ.get(cfg["api_key_env"], "")
        if not api_key:
            failures[name] = f"环境变量 {cfg['api_key_env']} 未设置，跳过"
            print(f"    [{name}] 跳过：{failures[name]}")
            continue

        print(f"    [{name}] {cfg['model']} 评测中... (timeout={cfg.get('timeout', 180)}s)")
        try:
            fn = _build_evaluator_fn(cfg)
            result = fn(query, agent_response, system_prompt, iteration, data_context)
            per_evaluator[name] = result
            print(f"    [{name}] 完成，加权分 = {result['weighted_score']:.1f}")
        except KeyboardInterrupt:
            print(f"\n    [中断] 用户中断，跳过剩余评测器，使用已完成结果（{list(per_evaluator.keys())}）")
            break
        except Exception as exc:
            failures[name] = str(exc)
            print(f"    [{name}] 失败：{exc}")

    if not per_evaluator:
        raise RuntimeError(
            f"所有评测器均调用失败：{failures}"
        )

    # ── 集成：加权平均各维度分数 ──────────────────────────────
    dims = list(RUBRIC.keys())
    weights = {
        name: enabled[name].get("weight", 1.0)
        for name in per_evaluator
    }
    total_weight = sum(weights.values())

    ensemble_scores: dict[str, float] = {}
    for dim in dims:
        weighted_sum = sum(
            per_evaluator[name]["scores"][dim] * weights[name]
            for name in per_evaluator
        )
        ensemble_scores[dim] = round(weighted_sum / total_weight, 2)

    # ── 各维度标准差（一致性指标） ────────────────────────────
    evaluator_std: dict[str, float] = {}
    for dim in dims:
        dim_scores = [per_evaluator[n]["scores"][dim] for n in per_evaluator]
        if len(dim_scores) > 1:
            mean = sum(dim_scores) / len(dim_scores)
            variance = sum((s - mean) ** 2 for s in dim_scores) / len(dim_scores)
            evaluator_std[dim] = round(math.sqrt(variance), 2)
        else:
            evaluator_std[dim] = 0.0

    # ── 反馈来源：取集成加权分最高的评测器 ───────────────────
    best_evaluator_name = max(
        per_evaluator,
        key=lambda n: per_evaluator[n]["weighted_score"]
    )
    best_result = per_evaluator[best_evaluator_name]

    # 重建 feedback，分数用集成分替换，理由来自最佳评测器
    feedback: dict[str, dict] = {}
    for dim in dims:
        fb = dict(best_result["feedback"][dim])  # shallow copy
        fb["score"] = ensemble_scores[dim]
        fb["source_evaluator"] = best_evaluator_name
        feedback[dim] = fb

    return {
        "scores":          ensemble_scores,
        "weighted_score":  calculate_weighted_score(ensemble_scores),
        "feedback":        feedback,
        "overall_comment": best_result["overall_comment"],
        "prompt_weakness": best_result["prompt_weakness"],
        "per_evaluator":   per_evaluator,
        "evaluator_std":   evaluator_std,
        "evaluators_used": list(per_evaluator.keys()),
        "evaluators_failed": failures,
    }


# ============================================================
# 集成汇总工具
# ============================================================

def aggregate_ensemble_results(eval_results: list[dict]) -> dict:
    """
    汇总多条集成评测结果，增加跨测试用例的一致性统计。

    Returns:
        {
            "avg_scores":         {dim: avg},
            "avg_weighted_score": float,
            "worst_dimensions":   [(dim, score), ...],
            "avg_evaluator_std":  {dim: avg_std},   # 平均评测者分歧
            "evaluators_used":    set,
        }
    """
    if not eval_results:
        return {}

    dims = list(RUBRIC.keys())

    avg_scores = {
        d: round(sum(r["scores"][d] for r in eval_results) / len(eval_results), 2)
        for d in dims
    }
    avg_weighted = round(
        sum(r["weighted_score"] for r in eval_results) / len(eval_results), 2
    )
    worst = sorted(avg_scores.items(), key=lambda x: x[1])[:3]

    avg_std: dict[str, float] = {}
    for d in dims:
        stds = [r.get("evaluator_std", {}).get(d, 0.0) for r in eval_results]
        avg_std[d] = round(sum(stds) / len(stds), 2) if stds else 0.0

    all_used: set[str] = set()
    for r in eval_results:
        all_used.update(r.get("evaluators_used", []))

    return {
        "avg_scores":         avg_scores,
        "avg_weighted_score": avg_weighted,
        "worst_dimensions":   worst,
        "avg_evaluator_std":  avg_std,
        "evaluators_used":    sorted(all_used),
    }
