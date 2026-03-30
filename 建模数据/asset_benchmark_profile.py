"""四大类资产 Benchmark Profile（基准画像）

读取已计算好的月收益率（plan_a_returns.csv）和 CGB_1Y 无风险利率（建模月频序列.csv），
输出 1Y/3Y/5Y 窗口的年化收益、年化波动率、Sharpe Ratio。

输入：
  - plan_a_returns.csv     — 方案A 4条资产腿月收益率（由 plan_a_modeling.py 生成）
  - 建模月频序列.csv        — 取 CGB_1Y 列（年化收益率 %，如 1.26 = 1.26%）

输出：
  - asset_benchmark_profile.csv — 4行（CASH/BOND/EQUITY/ALT）× 9列指标

列说明：
  - ann_return_{W}   — 年化收益率 = mean(月收益) × 12
  - ann_vol_{W}      — 年化波动率 = std(月收益) × √12
  - sharpe_ratio_{W} — 夏普比率 = mean(月超额收益) / std(月超额收益) × √12
                       其中月超额收益 = 资产月收益 − CGB_1Y 月化无风险利率

Usage:
    python3 建模数据/asset_benchmark_profile.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

DIR = Path(__file__).resolve().parent
RETURNS_CSV = DIR / "plan_a_returns.csv"      # 已计算好的4腿月收益率
RAW_CSV = DIR / "建模月频序列.csv"              # 原始月频数据（取 CGB_1Y）
OUT_CSV = DIR / "asset_benchmark_profile.csv"  # 输出：基准画像

# 4条资产腿：现金 / 固收 / 股票 / 另类（70%黄金+30%商品）
RETURN_COLS = ["r_cash", "r_bond", "r_equity", "r_alt"]
ASSET_CLASSES = ["CASH", "BOND", "EQUITY", "ALT"]

# 滚动窗口：近1年 / 近3年 / 近5年
WINDOWS = {"1y": 12, "3y": 36, "5y": 60}


def main():
    # ── 读取已有数据 ──
    returns = pd.read_csv(RETURNS_CSV, index_col="month")
    rf_raw = pd.read_csv(RAW_CSV, index_col="month", usecols=["month", "CGB_1Y"])

    # CGB_1Y 为年化百分比（如 1.26），转为月度无风险利率（如 0.00105）
    rf_monthly = rf_raw["CGB_1Y"] / 100 / 12

    # 按 month 对齐收益率与无风险利率
    common = returns.index.intersection(rf_monthly.dropna().index)
    returns = returns.loc[common, RETURN_COLS]
    rf_monthly = rf_monthly.loc[common]

    # ── 逐资产、逐窗口计算 ──
    rows = []
    for asset, col in zip(ASSET_CLASSES, RETURN_COLS):
        row = {"asset_class": asset}
        for label, w in WINDOWS.items():
            r = returns[col].iloc[-w:]       # 最近 W 个月的资产收益
            rf = rf_monthly.iloc[-w:]        # 同期月度无风险利率
            excess = r - rf                  # 月度超额收益

            row[f"ann_return_{label}"] = r.mean() * 12                          # 年化收益
            row[f"ann_vol_{label}"] = r.std() * np.sqrt(12)                     # 年化波动率
            row[f"sharpe_ratio_{label}"] = excess.mean() / excess.std() * np.sqrt(12)  # 夏普比率
        rows.append(row)

    # ── 输出宽表 CSV ──
    col_order = [
        "asset_class",
        "ann_return_1y", "ann_return_3y", "ann_return_5y",
        "ann_vol_1y", "ann_vol_3y", "ann_vol_5y",
        "sharpe_ratio_1y", "sharpe_ratio_3y", "sharpe_ratio_5y",
    ]
    df = pd.DataFrame(rows, columns=col_order).round(4)
    df.to_csv(OUT_CSV, index=False)
    print(f"✓ {OUT_CSV}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
