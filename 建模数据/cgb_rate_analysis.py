"""CGB 国债收益率季末序列

读取 建模月频序列.csv 中的 CGB_1Y（1年期国债到期收益率）和 CGB_10Y（10年期），
按季末重采样，输出 2021Q1 至今的利率与期限利差序列。

输入：
  - 建模月频序列.csv — 月频原始数据，取 CGB_1Y、CGB_10Y 两列（单位：%）

输出：
  - cgb_summary_metrics.csv — 季末利率序列

列说明：
  - date           — 季末日期（如 2021-03-31）
  - quarter_label  — 季度标签（如 2021Q1）
  - CGB_1Y_YTM     — 1年期国债到期收益率（%），建模无风险利率主口径
  - CGB_10Y_YTM    — 10年期国债到期收益率（%），长端利率锚
  - term_spread    — 期限利差 = CGB_10Y − CGB_1Y（%），反映收益率曲线斜率

Usage:
    python3 建模数据/cgb_rate_analysis.py
"""

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_IN = BASE_DIR / "建模月频序列.csv"       # 原始月频数据
OUT_CSV = BASE_DIR / "cgb_summary_metrics.csv"  # 输出：季末利率序列


def main():
    df = pd.read_csv(CSV_IN, index_col=0, parse_dates=True)
    df.index.name = "date"
    df = df.sort_index()

    # 按季末重采样，取每季最后一个月的月末值
    quarterly = df[["CGB_1Y", "CGB_10Y"]].resample("QE").last().dropna()

    # 筛选 2021Q1（含）之后的数据
    quarterly = quarterly[quarterly.index >= "2021-01-01"].copy()

    # 期限利差 = 10年期 − 1年期
    quarterly["term_spread"] = quarterly["CGB_10Y"] - quarterly["CGB_1Y"]

    # 生成季度标签（如 2021Q1）
    quarterly["quarter_label"] = quarterly.index.map(
        lambda dt: f"{dt.year}Q{(dt.month - 1) // 3 + 1}"
    )

    out = (
        quarterly[["quarter_label", "CGB_1Y", "CGB_10Y", "term_spread"]]
        .rename(columns={"CGB_1Y": "CGB_1Y_YTM", "CGB_10Y": "CGB_10Y_YTM"})
        .round(2)
        .reset_index()
    )
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")

    out.to_csv(OUT_CSV, index=False)
    print(f"✓ {OUT_CSV}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
