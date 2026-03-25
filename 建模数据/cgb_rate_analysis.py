"""CGB 利率汇总分析

读取 建模数据/建模月频序列.csv，计算：
  - 输出一：无风险利率与长端利率汇总指标  → cgb_summary_metrics.csv
  - 输出二：TERM_SPREAD_10Y_1Y 季末观察序列 → term_spread_quarterly_view.csv

Usage:
    python 建模数据/cgb_rate_analysis.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CSV_IN   = BASE_DIR / "建模月频序列.csv"
OUT_SUMMARY  = BASE_DIR / "cgb_summary_metrics.csv"
OUT_SPREAD   = BASE_DIR / "term_spread_quarterly_view.csv"


# ---------------------------------------------------------------------------
# 1. 读取数据
# ---------------------------------------------------------------------------
df = pd.read_csv(CSV_IN, index_col=0, parse_dates=True, encoding="utf-8-sig")
df.index.name = "date"
df = df.sort_index()

cgb_1y  = df["CGB_1Y_月末值(%)"].dropna()
cgb_10y = df["CGB_10Y_月末值(%)"].dropna()


# ---------------------------------------------------------------------------
# 2. 辅助：窗口均值（样本不足返回 NaN）
# ---------------------------------------------------------------------------
def window_mean(series: pd.Series, n: int) -> float:
    """最近 n 个有效值的简单均值；不足 n 个返回 NaN。"""
    tail = series.dropna().iloc[-n:]
    return float(tail.mean()) if len(tail) == n else float("nan")


# ---------------------------------------------------------------------------
# 3. 输出一：汇总指标
# ---------------------------------------------------------------------------
windows = {"current": 1, "1y": 12, "3y": 36, "5y": 60, "10y": 120, "20y": 240}

summary: dict[str, float] = {}

for label, n in windows.items():
    if label == "current":
        summary["rf_current"]        = float(cgb_1y.iloc[-1])
        summary["long_rate_current"] = float(cgb_10y.iloc[-1])
    else:
        summary[f"rf_{label}"]        = window_mean(cgb_1y,  n)
        summary[f"long_rate_{label}"] = window_mean(cgb_10y, n)

# 列顺序
col_order = [
    "rf_current", "rf_1y", "rf_3y", "rf_5y", "rf_10y", "rf_20y",
    "long_rate_current", "long_rate_1y", "long_rate_3y",
    "long_rate_5y", "long_rate_10y", "long_rate_20y",
]
summary_df = (
    pd.DataFrame([summary], columns=col_order)
    .round(2)
)
summary_df.to_csv(OUT_SUMMARY, index=False, encoding="utf-8-sig")
print(f"✓ 汇总指标 → {OUT_SUMMARY}")
print(summary_df.to_string(index=False))


# ---------------------------------------------------------------------------
# 4. 期限利差月频序列
# ---------------------------------------------------------------------------
# 对齐两列，取共同有效日期
aligned = pd.DataFrame({
    "cgb_1y":  cgb_1y,
    "cgb_10y": cgb_10y,
}).dropna()
aligned["term_spread_10y_1y"] = aligned["cgb_10y"] - aligned["cgb_1y"]


# ---------------------------------------------------------------------------
# 5. 输出二：季末观察序列（2024Q4 至最新）
# ---------------------------------------------------------------------------
# 季末月：3月、6月、9月、12月的最后一个交易日
quarterly = aligned.resample("QE").last().dropna(subset=["term_spread_10y_1y"])

# 筛选 2024Q4（2024-12-31）及以后
start_qtr = pd.Timestamp("2024-10-01")
quarterly = quarterly[quarterly.index >= start_qtr].copy()

# 生成季度标签，如 "2024Q4"
def quarter_label(dt: pd.Timestamp) -> str:
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}Q{q}"

quarterly["quarter_label"] = quarterly.index.map(quarter_label)
quarterly.index.name = "date"

spread_out = (
    quarterly[["quarter_label", "term_spread_10y_1y"]]
    .reset_index()
    .assign(term_spread_10y_1y=lambda x: x["term_spread_10y_1y"].round(2))
    [["date", "quarter_label", "term_spread_10y_1y"]]
)
spread_out["date"] = spread_out["date"].dt.strftime("%Y-%m-%d")

spread_out.to_csv(OUT_SPREAD, index=False, encoding="utf-8-sig")
print(f"\n✓ 期限利差季末序列 → {OUT_SPREAD}")
print(spread_out.to_string(index=False))
