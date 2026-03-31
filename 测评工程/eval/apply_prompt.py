"""
将评测得到的最优提示词回写到 market_context.py

用法：
    python apply_prompt.py                          # 应用 eval_results/best_prompt.md
    python apply_prompt.py --from eval_results/prompt_v3.md  # 应用指定版本
    python apply_prompt.py --dry-run                # 预览变更，不实际写入

注意：脚本会自动备份原始文件为 market_context.py.bak
"""

import argparse
import re
import shutil
import sys
import os
from pathlib import Path

ROOT_DIR    = Path(__file__).parent.parent
TARGET_FILE = ROOT_DIR / "market_context.py"
RESULTS_DIR = Path(__file__).parent / "eval_results"


def apply_prompt(prompt_file: Path, dry_run: bool = False) -> bool:
    """
    将 prompt_file 中的提示词写入 market_context.py 的 SYSTEM_PROMPT 变量。

    Args:
        prompt_file: 包含新提示词内容的 .md 文件
        dry_run:     True 时只预览，不实际修改

    Returns:
        True 表示成功
    """
    if not prompt_file.exists():
        print(f"错误：找不到提示词文件 {prompt_file}")
        return False

    if not TARGET_FILE.exists():
        print(f"错误：找不到目标文件 {TARGET_FILE}")
        return False

    new_prompt = prompt_file.read_text(encoding="utf-8").strip()
    source_code = TARGET_FILE.read_text(encoding="utf-8")

    # 匹配 SYSTEM_PROMPT = """...""" 块（三引号字符串）
    pattern = r'(SYSTEM_PROMPT\s*=\s*""")(.*?)(""")'
    match = re.search(pattern, source_code, re.DOTALL)

    if not match:
        print("错误：在 market_context.py 中未找到 SYSTEM_PROMPT = \"\"\"...\"\"\" 定义")
        return False

    old_prompt = match.group(2).strip()

    if old_prompt == new_prompt:
        print("提示词内容与当前版本完全相同，无需更新。")
        return True

    # 构建新代码
    new_source = source_code[:match.start(2)] + f"\n{new_prompt}\n" + source_code[match.end(2):]

    # 展示 diff 预览
    _print_diff_preview(old_prompt, new_prompt)

    if dry_run:
        print("\n[dry-run] 未实际写入，移除 --dry-run 参数以应用更改。")
        return True

    # 备份原文件
    backup_file = TARGET_FILE.with_suffix(".py.bak")
    shutil.copy2(TARGET_FILE, backup_file)
    print(f"\n原文件已备份至: {backup_file}")

    # 写入新版本
    TARGET_FILE.write_text(new_source, encoding="utf-8")
    print(f"已将新提示词写入: {TARGET_FILE}")
    print(f"  新提示词来源: {prompt_file}")
    print(f"  字符数变化  : {len(old_prompt)} → {len(new_prompt)}")

    return True


def _print_diff_preview(old: str, new: str):
    """打印提示词变更的简洁摘要（不需要 diff 库）"""
    old_lines = old.splitlines()
    new_lines = new.splitlines()

    added   = [l for l in new_lines if l not in set(old_lines)]
    removed = [l for l in old_lines if l not in set(new_lines)]

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
        size = f.stat().st_size
        mtime = f.stat().st_mtime
        from datetime import datetime
        ts = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {f.name:25s}  {size:6d} 字节  {ts}")


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="将评测最优提示词回写到 market_context.py"
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

    # 确定要应用的提示词文件
    if args.prompt_file:
        pf = Path(args.prompt_file)
        if not pf.is_absolute():
            pf = Path(__file__).parent / args.prompt_file
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
