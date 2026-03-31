"""
评测结果报告查看器

用法：
    python report.py                          # 查看 eval_results/ 下最新的汇总
    python report.py --iteration 2            # 查看第 2 轮详细结果
    python report.py --diff 1 3               # 对比第 1 轮和第 3 轮提示词差异
    python report.py --scores                 # 仅显示各轮得分趋势
"""

import argparse
import json
import sys
import os
from pathlib import Path

# 加入父目录以便导入 eval_rubric
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eval_rubric import RUBRIC, score_summary
from eval_config import RESULTS_DIR


RESULTS_PATH = Path(__file__).parent / RESULTS_DIR


# ============================================================
# 汇总视图
# ============================================================

def show_summary():
    summary_file = RESULTS_PATH / "summary.json"
    if not summary_file.exists():
        print("找不到 summary.json，请先运行 eval_pipeline.py")
        return

    s = json.loads(summary_file.read_text(encoding="utf-8"))

    print("\n" + "=" * 62)
    print("  评测结果汇总")
    print("=" * 62)
    print(f"  完成时间  : {s['completed_at']}")
    print(f"  迭代轮次  : {s['total_iterations']}")
    print(f"  最佳分数  : {s['best_score']:.2f} / 10")
    print(f"  目标分数  : {s['score_threshold']}")
    status = "达到目标" if s["achieved_goal"] else "未达到目标"
    print(f"  结果状态  : {status}")

    print("\n  得分趋势:")
    for h in s["score_history"]:
        bar_val = int(h["score"] * 4)  # scale to 40 chars
        bar = "█" * bar_val + "░" * (40 - bar_val)
        print(f"    第 {h['iteration']} 轮  {bar}  {h['score']:.2f}")

    # 最佳提示词
    best_file = RESULTS_PATH / "best_prompt.md"
    if best_file.exists():
        print(f"\n  最佳提示词 : {best_file}")

    print("=" * 62 + "\n")


# ============================================================
# 单轮详情
# ============================================================

def show_iteration(n: int):
    iter_file = RESULTS_PATH / f"iteration_{n}.json"
    if not iter_file.exists():
        print(f"找不到 iteration_{n}.json")
        return

    data = json.loads(iter_file.read_text(encoding="utf-8"))

    print("\n" + "=" * 62)
    print(f"  第 {n} 轮评测详情")
    print("=" * 62)
    print(f"  时间       : {data['timestamp']}")
    print(f"  加权均分   : {data['avg_score']:.2f} / 10\n")

    agg = data.get("aggregated", {})
    if agg.get("avg_scores"):
        print("  各维度平均分:")
        print(score_summary(agg["avg_scores"]))

    print("\n  逐查询详情:")
    for i, er in enumerate(data.get("eval_results", []), 1):
        q = er.get("query", "N/A")
        print(f"\n  ── 测试用例 {i} ────────────────────────────────")
        print(f"  查询  : {q}")
        print(f"  加权分: {er['weighted_score']:.1f}")
        print(f"  整体评语: {er.get('overall_comment', '')}")

        print("\n  各维度:")
        for dim, fb in er.get("feedback", {}).items():
            print(f"    {fb['name']:12s}  {fb['score']:4.1f}/10  {fb['reason'][:70]}...")

        pw = er.get("prompt_weakness", "")
        if pw:
            print(f"\n  提示词缺陷分析:\n    {pw[:200]}...")

    print("=" * 62 + "\n")


# ============================================================
# 提示词 Diff（逐段对比）
# ============================================================

def show_diff(iter_a: int, iter_b: int):
    """对比两个迭代轮次使用的提示词"""
    import difflib

    def _get_prompt(n: int) -> str | None:
        # 第 1 轮用初始提示词（从 iteration_1.json 读取），其他轮读 prompt_vN.md
        iter_file = RESULTS_PATH / f"iteration_{n}.json"
        if iter_file.exists():
            data = json.loads(iter_file.read_text(encoding="utf-8"))
            return data.get("system_prompt", "")
        return None

    prompt_a = _get_prompt(iter_a)
    prompt_b = _get_prompt(iter_b)

    if prompt_a is None:
        print(f"找不到第 {iter_a} 轮的数据")
        return
    if prompt_b is None:
        print(f"找不到第 {iter_b} 轮的数据")
        return

    diff = difflib.unified_diff(
        prompt_a.splitlines(keepends=True),
        prompt_b.splitlines(keepends=True),
        fromfile=f"第 {iter_a} 轮提示词",
        tofile=f"第 {iter_b} 轮提示词",
        lineterm="",
    )

    lines = list(diff)
    if not lines:
        print(f"第 {iter_a} 轮与第 {iter_b} 轮的提示词完全相同。")
        return

    print(f"\n{'='*62}")
    print(f"  提示词 Diff：第 {iter_a} 轮 → 第 {iter_b} 轮")
    print(f"{'='*62}")

    for line in lines:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            print(f"  {line}")
        elif line.startswith("+"):
            print(f"  \033[32m{line}\033[0m")   # 绿色：新增
        elif line.startswith("-"):
            print(f"  \033[31m{line}\033[0m")   # 红色：删除
        else:
            print(f"  {line}")

    print(f"{'='*62}\n")


# ============================================================
# 仅得分趋势
# ============================================================

def show_scores():
    """打印所有已完成迭代的得分，带各维度明细"""
    iter_files = sorted(RESULTS_PATH.glob("iteration_*.json"))
    if not iter_files:
        print("尚无评测结果，请先运行 eval_pipeline.py")
        return

    print(f"\n{'='*62}")
    print("  各轮得分趋势")
    print(f"{'='*62}")
    print(f"  {'轮次':4s}  {'总分':6s}  " + "  ".join(
        f"{v['name'][:4]}" for v in RUBRIC.values()
    ))
    print(f"  {'─'*4}  {'─'*6}  " + "  ".join("─" * 4 for _ in RUBRIC))

    for f in iter_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        n = data["iteration"]
        avg = data["avg_score"]
        agg = data.get("aggregated", {})
        dim_scores = agg.get("avg_scores", {})
        dim_str = "  ".join(
            f"{dim_scores.get(d, 0.0):4.1f}" for d in RUBRIC
        )
        print(f"  第{n:2d}轮  {avg:5.2f}  {dim_str}")

    print(f"{'='*62}\n")


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="查看评测结果报告")
    parser.add_argument(
        "--iteration", "-i",
        type=int, default=None,
        help="查看指定轮次的详细结果",
    )
    parser.add_argument(
        "--diff", "-d",
        nargs=2, type=int, metavar=("FROM", "TO"),
        help="对比两轮提示词的差异（如 --diff 1 3）",
    )
    parser.add_argument(
        "--scores", "-s",
        action="store_true",
        help="只显示各轮得分趋势",
    )
    args = parser.parse_args()

    if not RESULTS_PATH.exists():
        print(f"结果目录不存在: {RESULTS_PATH}")
        print("请先运行 eval_pipeline.py")
        sys.exit(1)

    if args.diff:
        show_diff(args.diff[0], args.diff[1])
    elif args.iteration is not None:
        show_iteration(args.iteration)
    elif args.scores:
        show_scores()
    else:
        show_summary()
        show_scores()
