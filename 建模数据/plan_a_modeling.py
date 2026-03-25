"""方案A 大类资产建模数据加工

4条资产腿（现金/固收/股票/另类），另类 = 70%黄金 + 30%商品。
计算月收益率序列、多窗口相关性矩阵、预期收益、波动率、协方差矩阵。

Usage:
    python3 建模数据/plan_a_modeling.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

DIR = Path(__file__).resolve().parent

WINDOWS = [12, 24, 36, 60, 120, 180, 240]

# 内部计算列名
RETURN_COLS = ["r_cash", "r_bond", "r_equity", "r_alt"]

# 输出用统一命名
ASSET_CLASSES = ["CASH", "BOND", "EQUITY", "COMMODITY"]
COL_NAMES = [
    "cash_cn_mmf_return",
    "bond_cn_composite_fullprice_return",
    "equity_cn_csi300_return",
    "commodity_cn_nhci_return",
]

# 内部列 → 输出列 映射
_RET_TO_CLASS = dict(zip(RETURN_COLS, ASSET_CLASSES))
_RET_TO_COL = dict(zip(RETURN_COLS, COL_NAMES))


def main():
    # ── Step 1: 读取月频序列 ──
    df = pd.read_csv(DIR / "建模月频序列.csv", index_col="month")

    price_cols = ["CBA02201.CS", "CBOND_NEW_COMPOSITE_WEALTH", "CSI300_TR", "AU9999", "NHCI"]
    prices = df[price_cols].copy()

    # ── Step 2: 计算月收益率 ──
    rets_raw = prices.pct_change()

    returns = pd.DataFrame(index=rets_raw.index)
    returns["r_cash"] = rets_raw["CBA02201.CS"]
    returns["r_bond"] = rets_raw["CBOND_NEW_COMPOSITE_WEALTH"]
    returns["r_equity"] = rets_raw["CSI300_TR"]
    returns["r_alt"] = 0.7 * rets_raw["AU9999"] + 0.3 * rets_raw["NHCI"]

    returns = returns.dropna(how="all")

    # 保存月收益率序列
    out_returns = DIR / "plan_a_returns.csv"
    returns.to_csv(out_returns)
    print(f"月收益率序列已保存: {out_returns}")
    print(f"  {len(returns)} 行 × {len(returns.columns)} 列")
    print(f"  时间范围: {returns.index[0]} ~ {returns.index[-1]}")
    print()

    # ── Step 3: 多窗口计算，按窗口输出到子目录 ──
    out_dir = DIR / "plan_a_windows"
    out_dir.mkdir(exist_ok=True)

    for w in WINDOWS:
        tail = returns.tail(w).dropna()
        n_valid = len(tail)

        corr = tail[RETURN_COLS].corr()
        cov_monthly = tail[RETURN_COLS].cov()
        cov_annual = cov_monthly * 12
        sigma_monthly = tail[RETURN_COLS].std()
        sigma_annual = sigma_monthly * np.sqrt(12)
        mu_monthly = tail[RETURN_COLS].mean()
        mu_annual = 12 * mu_monthly

        print(f"{'='*60}")
        print(f"窗口 {w}M  (有效样本 {n_valid} 个月)")
        print(f"{'='*60}")

        # ── 相关性矩阵 CSV ──
        corr_out = pd.DataFrame(
            corr.values,
            index=RETURN_COLS,
            columns=RETURN_COLS,
        )
        corr_out.index = [_RET_TO_COL[c] for c in RETURN_COLS]
        corr_out.columns = [_RET_TO_COL[c] for c in RETURN_COLS]
        corr_out.index.name = "asset"
        corr_csv = out_dir / f"corr_{w}M.csv"
        corr_out.round(4).to_csv(corr_csv)

        print("\n相关性矩阵 (ρ):")
        print(corr_out.round(4).to_string())

        # ── 协方差矩阵 CSV ──
        cov_out = pd.DataFrame(
            cov_annual.values,
            index=RETURN_COLS,
            columns=RETURN_COLS,
        )
        cov_out.index = [_RET_TO_COL[c] for c in RETURN_COLS]
        cov_out.columns = [_RET_TO_COL[c] for c in RETURN_COLS]
        cov_out.index.name = "asset"
        cov_csv = out_dir / f"cov_{w}M.csv"
        cov_out.to_csv(cov_csv, float_format="%.6f")

        print("\n年化协方差矩阵 (Σ):")
        print(cov_out.round(6).to_string())

        # ── 波动率 CSV ──
        sigma_df = pd.DataFrame({
            "asset_class": ASSET_CLASSES,
            "sigma_ann": [sigma_annual[c] for c in RETURN_COLS],
        })
        sigma_csv = out_dir / f"sigma_{w}M.csv"
        sigma_df.round(4).to_csv(sigma_csv, index=False)

        print("\n年化波动率 (σ):")
        for _, row in sigma_df.iterrows():
            print(f"  {row['asset_class']:12s}  {row['sigma_ann']:.4f}")

        # ── 预期收益 CSV ──
        mu_df = pd.DataFrame({
            "asset_class": ASSET_CLASSES,
            "mu_monthly": [mu_monthly[c] for c in RETURN_COLS],
            "mu_annual": [mu_annual[c] for c in RETURN_COLS],
        })
        mu_csv = out_dir / f"mu_{w}M.csv"
        mu_df.round(6).to_csv(mu_csv, index=False)

        print("\n预期收益 (μ):")
        for _, row in mu_df.iterrows():
            print(f"  {row['asset_class']:12s}  月={row['mu_monthly']:+.4f}  "
                  f"年={row['mu_annual']:+.4f} ({row['mu_annual']*100:+.2f}%)")
        print()

    print(f"各窗口结果已保存至: {out_dir}/")
    print(f"  每个窗口 4 个文件: corr_WM.csv, cov_WM.csv, sigma_WM.csv, mu_WM.csv")

    # ── 无风险利率 ──
    rf = pd.read_csv(DIR / "cgb_summary_metrics.csv")
    print(f"\n无风险利率 (来自 cgb_summary_metrics.csv):")
    print(rf.to_string(index=False))


if __name__ == "__main__":
    main()
