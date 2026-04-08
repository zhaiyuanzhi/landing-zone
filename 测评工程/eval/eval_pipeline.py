"""
市场分析智能体 —— 自动化评测 & 提示词迭代 Pipeline

运行方式（在 eval/ 目录下）：
    python eval_pipeline.py                # 完整流程（评测 + 迭代优化）
    python eval_pipeline.py --eval-only    # 仅评测，不优化提示词
    python eval_pipeline.py --iterations 3 # 指定最大迭代次数

输出文件：
    eval_results/
    ├── iteration_1.json   # 每轮详细评测结果
    ├── iteration_2.json
    ├── prompt_v2.md       # 第 2 轮使用的提示词（即第 1 轮优化结果）
    ├── prompt_v3.md
    ├── best_prompt.md     # 历史最高分对应的提示词
    └── summary.json       # 总体结果摘要
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from eval_config import (
    SCORE_THRESHOLD,
    MAX_ITERATIONS,
    TEST_QUERIES,
    RESULTS_DIR,
    validate_config,
)
from agent_runner import run_market_agent
from evaluator import evaluate_response, aggregate_eval_results
from prompt_optimizer import optimize_prompt
from eval_rubric import RUBRIC, score_summary

# 初始提示词来自 eval 目录自包含的 Demo 数据（不依赖上级 market_context.py）
from demo_market_context import DEMO_SYSTEM_PROMPT as INITIAL_SYSTEM_PROMPT, DEMO_DATA_CONTEXT

# ============================================================
# 测评集动态加载
# ============================================================

QUERIES_FILE = Path(__file__).parent / "queries.json"


def load_effective_queries() -> list[str]:
    """
    加载有效的测评集：优先使用 queries.json（自定义），否则用默认 TEST_QUERIES。

    Returns:
        测评查询列表
    """
    if QUERIES_FILE.exists():
        try:
            data = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
            queries = data.get("queries", [])
            source = data.get("source", "unknown")
            updated_at = data.get("updated_at", "")

            if queries:
                print(f"\n  [测评集] 使用自定义测评集（来源：{source}）")
                print(f"  [测评集] 共 {len(queries)} 条测试查询")
                if updated_at:
                    print(f"  [测评集] 最近更新时间：{updated_at}")
                return queries
        except Exception as e:
            print(f"\n  [警告] 解析 queries.json 失败：{e}，回退到默认测评集")

    print(f"\n  [测评集] 使用默认测评集（来自 eval_config.TEST_QUERIES）")
    print(f"  [测评集] 共 {len(TEST_QUERIES)} 条测试查询")
    return TEST_QUERIES


# ============================================================
# 全局变量：有效测评集（在 run_pipeline 中初始化）
# ============================================================

effective_queries: list[str] = []

# ============================================================
# 主流程
# ============================================================

def run_pipeline(
    eval_only: bool = False,
    max_iterations: int | None = None,
    resume_from: str | None = None,
    force_regen: bool = False,
) -> dict:
    """
    执行完整的评测 & 迭代优化流程。

    Args:
        eval_only:      True 时只评测，不执行提示词优化
        max_iterations: 覆盖配置文件中的最大迭代次数
        resume_from:    从指定提示词文件恢复（如 eval_results/prompt_v3.md）
        force_regen:    True 时忽略已有回答文件，强制重新调用智能体

    Returns:
        summary dict
    """
    global effective_queries
    # ── 加载有效的测评集（优先使用 queries.json）───────────────
    effective_queries = load_effective_queries()


    validate_config()

    results_dir = Path(__file__).parent / RESULTS_DIR
    results_dir.mkdir(exist_ok=True)

    effective_max_iter = max_iterations or MAX_ITERATIONS

    _header(eval_only, effective_max_iter)

    # 加载起始提示词：优先使用 --resume-from 指定的文件
    if resume_from:
        resume_path = Path(resume_from)
        if not resume_path.is_absolute():
            resume_path = Path(__file__).parent / resume_from
        if not resume_path.exists():
            raise FileNotFoundError(f"找不到指定的提示词文件: {resume_path}")
        current_prompt = resume_path.read_text(encoding="utf-8")
        print(f"  从已保存提示词恢复: {resume_path.name}")
    else:
        current_prompt = INITIAL_SYSTEM_PROMPT
    best_score     = 0.0
    best_prompt    = current_prompt
    history        = []

    for iteration in range(1, effective_max_iter + 1):
        print(f"\n{'='*68}")
        print(f"  第 {iteration} 轮 / 共 {effective_max_iter} 轮")
        print(f"{'='*68}")

        # ── Step 1: 调用智能体 ────────────────────────────────────
        agent_results = _run_agents(iteration, current_prompt, results_dir, force_regen)
        if not agent_results:
            print("  所有智能体调用均失败，终止流程。")
            break

        # ── Step 2: Claude 评测 ───────────────────────────────────
        eval_results = _run_evaluations(iteration, agent_results, current_prompt)
        if not eval_results:
            print("  所有评测均失败，终止流程。")
            break

        # ── Step 3: 汇总本轮结果 ──────────────────────────────────
        agg = aggregate_eval_results(eval_results)
        avg_score = agg["avg_weighted_score"]

        print(f"\n  本轮加权均分: {avg_score:.2f} / 10  （目标 {SCORE_THRESHOLD}）")
        print(f"\n  维度得分详情:")
        print(score_summary(agg["avg_scores"]))

        # 更新最佳
        if avg_score > best_score:
            best_score  = avg_score
            best_prompt = current_prompt

        # 保存本轮数据
        iter_data = {
            "iteration":    iteration,
            "timestamp":    datetime.now().isoformat(),
            "system_prompt": current_prompt,
            "avg_score":    avg_score,
            "aggregated":   agg,
            "eval_results": eval_results,
        }
        _save_json(results_dir / f"iteration_{iteration}.json", iter_data)
        history.append({"iteration": iteration, "score": avg_score})

        # ── Step 4: 达到目标则停止 ────────────────────────────────
        if avg_score >= SCORE_THRESHOLD:
            print(f"\n  达到目标分数 {SCORE_THRESHOLD}，停止迭代。")
            break

        if iteration == effective_max_iter:
            print(f"\n  达到最大迭代次数 {effective_max_iter}，停止。")
            break

        if eval_only:
            print("\n  --eval-only 模式，跳过提示词优化。")
            break

        # ── Step 5: 优化提示词 ────────────────────────────────────
        new_prompt = _run_optimization(
            iteration, current_prompt, eval_results, results_dir
        )
        if new_prompt:
            current_prompt = new_prompt
        else:
            print("  提示词优化失败，保持当前版本继续评测。")

        time.sleep(2)  # 避免触发速率限制

    # ── 保存最佳提示词 & 汇总 ─────────────────────────────────────
    best_prompt_file = results_dir / "best_prompt.md"
    best_prompt_file.write_text(best_prompt, encoding="utf-8")

    summary = {
        "completed_at":     datetime.now().isoformat(),
        "total_iterations": len(history),
        "best_score":       best_score,
        "score_threshold":  SCORE_THRESHOLD,
        "achieved_goal":    best_score >= SCORE_THRESHOLD,
        "score_history":    history,
    }
    _save_json(results_dir / "summary.json", summary)

    _footer(summary, best_prompt_file)
    return summary


# ============================================================
# 子步骤
# ============================================================

def _run_agents(
    iteration: int,
    system_prompt: str,
    results_dir: Path,
    force_regen: bool = False,
) -> list[dict]:
    """
    调用智能体，返回成功的结果列表，并将每条回答落盘为可读 Markdown 文件。

    若 force_regen=False 且当前轮次所有回答文件均已存在，则直接加载文件跳过 LLM 调用。
    """
    responses_dir = results_dir / "responses"
    responses_dir.mkdir(exist_ok=True)

    total = len(effective_queries)

    # ── 缓存命中：文件全部已存在且不强制重新生成 ───────────────
    if not force_regen:
        cached = _try_load_cached_responses(iteration, responses_dir, total)
        if cached is not None:
            print(f"\n  [智能体调用] 发现第 {iteration} 轮全部 {total} 条回答文件，直接加载")
            print(f"  提示：若需重新生成，请添加 --force-regen 参数")
            for i, r in enumerate(cached, 1):
                print(f"  [{i}/{total}] 已加载: iter{iteration}_q{i}.md  ({len(r['response'])} 字符)")
            return cached

    # ── 正常调用 LLM ──────────────────────────────────────────
    results = []
    print(f"\n  [智能体调用] 共 {total} 个测试查询")

    for i, query in enumerate(effective_queries, 1):
        short_q = query[:55] + "..." if len(query) > 55 else query
        print(f"  [{i}/{total}] {short_q}")

        result = run_market_agent(query=query, system_prompt=system_prompt)
        if result["error"]:
            print(f"         ERROR: {result['error']}")
            continue

        char_len = len(result["response"])
        tokens   = result["prompt_tokens"] + result["completion_tokens"]
        print(f"         OK — {char_len} 字符 / {tokens} tokens")

        resp_file = responses_dir / f"iter{iteration}_q{i}.md"
        _save_response_md(resp_file, iteration, i, query, result["response"], tokens, DEMO_DATA_CONTEXT)
        print(f"         已保存: {resp_file.relative_to(results_dir.parent)}")

        results.append({
            "query":    query,
            "response": result["response"],
            "tokens":   tokens,
        })

    return results


def _try_load_cached_responses(
    iteration: int,
    responses_dir: Path,
    total: int,
) -> list[dict] | None:
    """
    检查当前轮次所有回答文件是否齐全；齐全则解析并返回，否则返回 None。
    """
    results = []
    for i in range(1, total + 1):
        path = responses_dir / f"iter{iteration}_q{i}.md"
        if not path.exists():
            return None
        record = _parse_response_md(path)
        if record is None:
            return None  # 文件损坏，重新生成
        results.append(record)
    return results


def _parse_response_md(path: Path) -> dict | None:
    """
    解析 _save_response_md 写出的 Markdown 文件，返回 {query, response, tokens}。
    文件格式：
        # 第 N 轮 · 查询 M
        **查询：** {query}
        **Tokens：** {tokens}
        ---
        {response}
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    # 提取 query
    query = ""
    for line in text.splitlines():
        if line.startswith("**查询：**"):
            query = line.removeprefix("**查询：**").strip()
            break
    if not query:
        return None

    # 提取 tokens
    tokens = 0
    for line in text.splitlines():
        if line.startswith("**Tokens：**"):
            try:
                tokens = int(line.removeprefix("**Tokens：**").strip())
            except ValueError:
                pass
            break

    # 提取 response（第一个 "---\n\n" 之后、附录数据标记之前的内容）
    sep = "\n---\n\n"
    idx = text.find(sep)
    if idx == -1:
        return None
    after_sep = text[idx + len(sep):]

    # 去除末尾附录数据区块（_save_response_md 写入的市场数据部分）
    data_marker = "\n---\n\n## 附："
    dm_idx = after_sep.find(data_marker)
    if dm_idx != -1:
        response = after_sep[:dm_idx].rstrip("\n")
    else:
        response = after_sep.rstrip("\n")

    return {"query": query, "response": response, "tokens": tokens}


def _save_response_md(
    path: Path,
    iteration: int,
    q_index: int,
    query: str,
    response: str,
    tokens: int,
    data_context: str = "",
) -> None:
    data_section = ""
    if data_context:
        data_section = (
            f"\n---\n\n"
            f"## 附：提供给模型的市场数据（仅供核查）\n\n"
            f"{data_context}\n"
        )
    content = (
        f"# 第 {iteration} 轮 · 查询 {q_index}\n\n"
        f"**查询：** {query}\n\n"
        f"**Tokens：** {tokens}\n\n"
        f"---\n\n"
        f"{response}"
        f"{data_section}"
    )
    path.write_text(content, encoding="utf-8")


def _run_evaluations(
    iteration: int,
    agent_results: list[dict],
    system_prompt: str,
) -> list[dict]:
    """逐条评测，返回含 query 字段的评测结果列表"""
    results = []
    total = len(agent_results)
    print(f"\n  [Claude 评测] 共 {total} 条回复")

    for i, ar in enumerate(agent_results, 1):
        short_q = ar["query"][:50] + "..." if len(ar["query"]) > 50 else ar["query"]
        print(f"  [{i}/{total}] 评测中：{short_q}")

        try:
            eval_result = evaluate_response(
                query=ar["query"],
                agent_response=ar["response"],
                system_prompt=system_prompt,
                iteration=iteration,
                data_context=DEMO_DATA_CONTEXT,
            )
            eval_result["query"] = ar["query"]
            results.append(eval_result)
            print(f"         加权分 = {eval_result['weighted_score']:.1f}")
        except Exception as exc:
            print(f"         ERROR: {exc}")

    return results


def _run_optimization(
    iteration: int,
    current_prompt: str,
    eval_results: list[dict],
    results_dir: Path,
) -> str | None:
    """执行提示词优化，成功时返回新提示词并保存文件"""
    print(f"\n  [提示词优化] 基于 {len(eval_results)} 条评测结果生成第 {iteration+1} 版提示词...")

    try:
        opt = optimize_prompt(
            current_prompt=current_prompt,
            eval_results=eval_results,
            iteration=iteration,
        )
    except Exception as exc:
        print(f"  优化器异常: {exc}")
        return None

    if not opt["optimized_prompt"]:
        print("  未能从优化器输出中提取新提示词。")
        return None

    # 保存新提示词
    prompt_file = results_dir / f"prompt_v{iteration + 1}.md"
    prompt_file.write_text(opt["optimized_prompt"], encoding="utf-8")
    print(f"  新提示词已保存: {prompt_file.name}")

    if opt["changes_summary"]:
        print("\n  改动摘要:")
        for line in opt["changes_summary"].splitlines():
            if line.strip():
                print(f"    {line}")

    if opt["expected_improvements"]:
        print("\n  预期改善:")
        for line in opt["expected_improvements"].splitlines():
            if line.strip():
                print(f"    {line}")

    # 保存完整优化记录
    _save_json(
        results_dir / f"optimization_{iteration}.json",
        {
            "from_iteration":     iteration,
            "changes_summary":    opt["changes_summary"],
            "expected_improvements": opt["expected_improvements"],
        },
    )

    return opt["optimized_prompt"]


# ============================================================
# 工具函数
# ============================================================

def _save_json(path: Path, data: dict):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _header(eval_only: bool, max_iter: int):
    mode_str = "仅评测" if eval_only else f"评测 + 迭代优化（最多 {max_iter} 轮）"
    print("\n" + "=" * 68)
    print("  市场分析智能体  ·  自动化评测 & 提示词迭代 Pipeline")
    print("=" * 68)
    print(f"  模式       : {mode_str}")
    print(f"  智能体模型 : qwen3-235b-a22b-instruct-2507")
    print(f"  评测模型   : claude-opus-4-6 (adaptive thinking)")
    print(f"  测试用例   : {len(effective_queries)} 条")
    print(f"  目标分数   : {SCORE_THRESHOLD} / 10")
    print(f"  评分维度   : {len(RUBRIC)} 个（{' / '.join(v['name'] for v in RUBRIC.values())}）")
    print("=" * 68)


def _footer(summary: dict, best_prompt_file: Path):
    print("\n" + "=" * 68)
    status = "达到目标" if summary["achieved_goal"] else "未达到目标"
    print(f"  Pipeline 完成  [{status}]")
    print(f"  迭代轮次    : {summary['total_iterations']}")
    print(f"  最佳分数    : {summary['best_score']:.2f} / 10  （目标 {summary['score_threshold']}）")
    print(f"  得分趋势    : " + " → ".join(
        f"{h['score']:.2f}" for h in summary["score_history"]
    ))
    print(f"  最佳提示词  : {best_prompt_file}")
    print(f"  详细结果    : {best_prompt_file.parent}/")
    print("=" * 68 + "\n")


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="市场分析智能体评测 & 提示词迭代")
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="只评测，不执行提示词优化",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help=f"最大迭代次数（默认使用配置文件中的 {MAX_ITERATIONS}）",
    )
    parser.add_argument(
        "--resume-from",
        type=str,
        default=None,
        metavar="PROMPT_FILE",
        help="从已保存的提示词文件恢复（如 eval_results/prompt_v3.md）",
    )
    parser.add_argument(
        "--force-regen",
        action="store_true",
        help="强制重新调用智能体生成回答，忽略已有的 iter{N}_q{M}.md 缓存文件",
    )
    args = parser.parse_args()

    run_pipeline(
        eval_only=args.eval_only,
        max_iterations=args.iterations,
        resume_from=args.resume_from,
        force_regen=args.force_regen,
    )
