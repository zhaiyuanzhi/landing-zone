"""
评测器对外接口（向后兼容入口）

eval_pipeline.py 只需 import 这里的两个公开函数：
  - evaluate_response(...)     → 调用集成评测器
  - aggregate_eval_results(...)→ 汇总多条结果

内部实际委托给 evaluator_ensemble.py 执行多模型评测。
"""

from eval_config import EVALUATOR_CONFIGS
from evaluator_ensemble import evaluate_ensemble, aggregate_ensemble_results


def evaluate_response(
    query: str,
    agent_response: str,
    system_prompt: str,
    iteration: int = 0,
    data_context: str = "",
) -> dict:
    """
    对单条智能体回复进行多模型集成评测。

    Args:
        data_context: 提供给智能体的市场数据原文，用于评测器核查 data_accuracy

    返回值格式与旧版保持兼容，额外增加：
      per_evaluator   : {evaluator_name: result}  各评测器原始分
      evaluator_std   : {dim: std}                各维度评测者分歧值
      evaluators_used : [name, ...]               成功的评测器列表
    """
    return evaluate_ensemble(
        query=query,
        agent_response=agent_response,
        system_prompt=system_prompt,
        iteration=iteration,
        evaluator_configs=EVALUATOR_CONFIGS,
        data_context=data_context,
    )


def aggregate_eval_results(eval_results: list[dict]) -> dict:
    """
    汇总多条集成评测结果，计算均分、最差维度、评测者一致性统计。
    """
    return aggregate_ensemble_results(eval_results)
