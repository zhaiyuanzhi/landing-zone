"""
将评测得到的最优提示词回写到 市场分析-提示词模板.md

模板文件结构：
    [提示词区块]          ← 任务目标、角色、约束条件（本脚本负责更新这部分）
    # 宏观经济数据
    [数据区块]            ← 全部 CSV 数据（本脚本不改动这部分）

用法：
    python apply_prompt.py                                   # 应用 eval_results/best_prompt.md
    python apply_prompt.py --from eval_results/prompt_v3.md  # 应用指定版本
    python apply_prompt.py --dry-run                         # 预览变更，不实际写入
    python apply_prompt.py --list                            # 列出可用的提示词文件
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

EVAL_DIR    = Path(__file__).parent
TARGET_FILE = EVAL_DIR / "市场分析-提示词模板.md"
RESULTS_DIR = EVAL_DIR / "eval_results"
SPLIT_MARKER = "\n# 宏观经济数据\n"


def apply_prompt(prompt_file: Path, dry_run: bool = False) -> bool:
    """
    用 prompt_file 中的内容替换模板文件的提示词区块，数据区块保持不变。

    Args:
        prompt_file: 包含新提示词的 .md 文件（仅提示词部分，不含数据）
        dry_run:     True 时只预览，不实际写入

    Returns:
        True 表示成功
    """
    if not prompt_file.exists():
        print(f"错误：找不到提示词文件 {prompt_file}")
        return False

    if not TARGET_FILE.exists():
        print(f"错误：找不到模板文件 {TARGET_FILE}")
        return False

    new_prompt = prompt_file.read_text(encoding="utf-8").strip()
    template   = TARGET_FILE.read_text(encoding="utf-8")

    if SPLIT_MARKER not in template:
        print(f"错误：模板文件中未找到分隔标记 '# 宏观经济数据'")
        print("请确认 市场分析-提示词模板.md 包含该一级标题。")
        return False

    old_prompt, data_section = template.split(SPLIT_MARKER, 1)
    old_prompt = old_prompt.strip()

    if old_prompt == new_prompt:
        print("提示词内容与当前版本完全相同，无需更新。")
        return True

    _print_diff_preview(old_prompt, new_prompt)

    if dry_run:
        print("\n[dry-run] 未实际写入，移除 --dry-run 参数以应用更改。")
        return True

    # 备份原文件
    backup_file = TARGET_FILE.with_suffix(".md.bak")
    shutil.copy2(TARGET_FILE, backup_file)
    print(f"\n原文件已备份至: {backup_file.name}")

    # 写入：新提示词 + 分隔标记 + 原数据区块
    new_template = new_prompt + SPLIT_MARKER + data_section
    TARGET_FILE.write_text(new_template, encoding="utf-8")

    print(f"已更新: {TARGET_FILE.name}")
    print(f"  来源文件  : {prompt_file.name}")
    print(f"  字符数变化: {len(old_prompt)} → {len(new_prompt)}")

    return True


def _print_diff_preview(old: str, new: str):
    """打印提示词变更的简洁摘要"""
    old_lines = old.splitlines()
    new_lines  = new.splitlines()
    old_set    = set(old_lines)
    new_set    = set(new_lines)

    added   = [l for l in new_lines if l not in old_set]
    removed = [l for l in old_lines if l not in new_set]

    print("\n" + "=" * 60)
    print("  提示词变更预览")
    print("=" * 60)
    print(f"  原始行数: {len(old_lines)}  →  新版行数: {len(new_lines)}")
    print(f"  净增减  : +{len(added)} 行 / -{len(removed)} 行\n")

    if removed:
        print("  ── 删除的行（前 5 条）:")
        for line in removed[:5]:
            if line.strip():
                print(f"    \033[31m- {line[:80]}\033[0m")

    if added:
        print("\n  ── 新增的行（前 5 条）:")
        for line in added[:5]:
            if line.strip():
                print(f"    \033[32m+ {line[:80]}\033[0m")

    print("=" * 60)


def list_available_prompts():
    """列出所有可用的已保存提示词文件"""
    if not RESULTS_DIR.exists():
        print("尚无评测结果，请先运行 eval_pipeline.py")
        return

    files = sorted(RESULTS_DIR.glob("prompt_v*.md")) + list(RESULTS_DIR.glob("best_prompt.md"))
    if not files:
        print("eval_results/ 中没有找到保存的提示词文件")
        return

    print("\n可用的提示词文件:")
    for f in files:
        size  = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {f.name:25s}  {size:6d} 字节  {mtime}")


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="将评测最优提示词回写到 市场分析-提示词模板.md（保留数据区块不变）"
    )
    parser.add_argument(
        "--from",
        dest="prompt_file",
        type=str,
        default=None,
        metavar="PROMPT_FILE",
        help="指定提示词文件（默认使用 eval_results/best_prompt.md）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览变更，不实际写入文件",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用的已保存提示词文件",
    )
    args = parser.parse_args()

    if args.list:
        list_available_prompts()
        sys.exit(0)

    if args.prompt_file:
        pf = Path(args.prompt_file)
        if not pf.is_absolute():
            pf = EVAL_DIR / args.prompt_file
    else:
        pf = RESULTS_DIR / "best_prompt.md"
        if not pf.exists():
            print("找不到 eval_results/best_prompt.md，请先运行 eval_pipeline.py")
            print("或使用 --from 指定提示词文件")
            print()
            list_available_prompts()
            sys.exit(1)

    success = apply_prompt(pf, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
