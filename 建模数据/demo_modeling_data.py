"""Demo: 大类资产建模数据加工

从 data/raw/ 读取原始 Excel，加工为建模所需的月频序列，输出到 CSV。

Step 1: CGB_1Y → 月频无风险利率 r_f
Step 2: 扩展至全部 6 个建模指标（方案 A 五条资产腿 + r_f）+ CGB_10Y

Usage:
    python docs/建模数据/demo_modeling_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT_DIR = Path(__file__).resolve().parent
OUT_FILE = OUT_DIR / "建模月频序列.csv"


# ---------------------------------------------------------------------------
# 1. 读取 Choice 导出格式（带 10 行元数据头）
# ---------------------------------------------------------------------------

def read_choice_indicator(filepath: str, col_index: int = 2) -> pd.Series:
    """Read a Choice-exported indicator file (序号/日期/值 format).

    Args:
        filepath: Path to the .xlsx file.
        col_index: Column index for the value (0-based). Default 2 (3rd column).

    Returns:
        pd.Series with DatetimeIndex, name = indicator name from header row.
    """
    df = pd.read_excel(filepath, header=None)
    # Row 0 has column headers: 序号, 日期, indicator_name, ...
    indicator_name = df.iloc[0, col_index]
    # Data starts at row 10 (after 10 metadata rows)
    data = df.iloc[10:, [1, col_index]].copy()
    data.columns = ["date", "value"]
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["value"] = pd.to_numeric(data["value"], errors="coerce")
    data = data.dropna(subset=["date", "value"]).set_index("date").sort_index()
    return data["value"].rename(indicator_name)


def read_kline_close(filepath: str) -> pd.Series:
    """Read a Choice K-line exported file, extract close price.

    Format: row 0 = header (证券代码, 证券名称, 交易时间, 开盘价, ..., 收盘价, ...)
    Close price is column index 6.
    """
    df = pd.read_excel(filepath, header=None)
    name = str(df.iloc[0, 0])  # e.g. "证券代码" — use first data row instead
    sec_name = df.iloc[1, 1]   # e.g. "沪深300全收益"
    data = df.iloc[1:, [2, 6]].copy()
    data.columns = ["date", "close"]
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.dropna(subset=["date", "close"]).set_index("date").sort_index()
    return data["close"].rename(sec_name)


def read_cba02201(filepath: str) -> pd.Series:
    """Read CBA02201.CS (中债货基指数) — Choice 行情导出格式，取收盘价列。

    Format: row 0 = header, data rows sorted descending by date.
    Columns: 交易日期(0), ..., 收盘价(4)
    """
    df = pd.read_excel(filepath, header=None)
    data = df.iloc[1:, [0, 4]].copy()
    data.columns = ["date", "close"]
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.dropna(subset=["date", "close"]).set_index("date").sort_index()
    return data["close"].rename("CBA02201.CS")


# ---------------------------------------------------------------------------
# 2. 日频 → 月频（取每月最后一个有效交易日）
# ---------------------------------------------------------------------------

def to_month_end(series: pd.Series) -> pd.Series:
    """Resample daily series to monthly using last valid observation."""
    return series.resample("ME").last().dropna()


# ---------------------------------------------------------------------------
# 3. 加工逻辑
# ---------------------------------------------------------------------------

def compute_rf(cgb1y_monthly: pd.Series) -> pd.Series:
    """CGB_1Y (%) → 月频无风险收益率 r_f,t = (1 + CGB_1Y/100)^(1/12) - 1"""
    return ((1 + cgb1y_monthly / 100) ** (1 / 12) - 1).rename("r_f")


def compute_log_return(price_monthly: pd.Series, name: str) -> pd.Series:
    """Price index → monthly log return: ln(P_t / P_{t-1})"""
    return np.log(price_monthly / price_monthly.shift(1)).dropna().rename(name)


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("大类资产建模数据加工 Demo")
    print("=" * 60)

    results = {}

    # --- CGB_1Y: 无风险利率 ---
    cgb1y_daily = read_choice_indicator(
        RAW_DIR / "daily" / "bond_CGB_1y.xlsx", col_index=2
    )
    cgb1y_monthly = to_month_end(cgb1y_daily).rename("CGB_1Y_pct")
    rf = compute_rf(cgb1y_monthly)
    results["CGB_1Y_月末值(%)"] = cgb1y_monthly
    results["r_f_月频"] = rf
    print(f"\n[CGB_1Y] 日频 {len(cgb1y_daily)} 条 → 月频 {len(cgb1y_monthly)} 条")
    print(f"  最新月: {cgb1y_monthly.index[-1]:%Y-%m}  CGB_1Y={cgb1y_monthly.iloc[-1]:.4f}%  r_f={rf.iloc[-1]:.6f}")

    # --- CSI300_TR: 股票主腿（方案A） ---
    csi300tr_daily = read_kline_close(RAW_DIR / "daily" / "K线导出_H00300_日线数据.xlsx")
    csi300tr_monthly = to_month_end(csi300tr_daily).rename("CSI300_TR")
    r_equity = compute_log_return(csi300tr_monthly, "r_equity_A")
    results["CSI300_TR_月末值"] = csi300tr_monthly
    results["r_equity_A"] = r_equity
    print(f"\n[CSI300_TR] 日频 {len(csi300tr_daily)} 条 → 月频 {len(csi300tr_monthly)} 条")

    # --- AU9999: 黄金主腿 ---
    au_daily = read_kline_close(RAW_DIR / "daily" / "K线导出_AU9999_日线数据.xlsx")
    au_monthly = to_month_end(au_daily).rename("AU9999")
    r_gold = compute_log_return(au_monthly, "r_gold_A")
    results["AU9999_月末值"] = au_monthly
    results["r_gold_A"] = r_gold
    print(f"\n[AU9999] 日频 {len(au_daily)} 条 → 月频 {len(au_monthly)} 条")

    # --- NHCI: 商品主腿 ---
    nhci_daily = read_kline_close(RAW_DIR / "daily" / "K线导出_NHCI_日线数据.xlsx")
    nhci_monthly = to_month_end(nhci_daily).rename("NHCI")
    r_cmdty = compute_log_return(nhci_monthly, "r_cmdty_A")
    results["NHCI_月末值"] = nhci_monthly
    results["r_cmdty_A"] = r_cmdty
    print(f"\n[NHCI] 日频 {len(nhci_daily)} 条 → 月频 {len(nhci_monthly)} 条")

    # --- CGB_10Y: 10年国债收益率 ---
    cgb10y_daily = read_choice_indicator(
        RAW_DIR / "daily" / "cn_bond_credit_rates_daily.xlsx", col_index=4
    )
    cgb10y_monthly = to_month_end(cgb10y_daily).rename("CGB_10Y_pct")
    results["CGB_10Y_月末值(%)"] = cgb10y_monthly
    print(f"\n[CGB_10Y] 日频 {len(cgb10y_daily)} 条 → 月频 {len(cgb10y_monthly)} 条")
    print(f"  最新月: {cgb10y_monthly.index[-1]:%Y-%m}  CGB_10Y={cgb10y_monthly.iloc[-1]:.4f}%")

    # --- CBOND_NEW_COMPOSITE_WEALTH: 固收主腿（方案A） ---
    cbond_daily = read_choice_indicator(
        RAW_DIR / "daily" / "cn_bond_credit_rates_daily.xlsx", col_index=2
    )
    cbond_monthly = to_month_end(cbond_daily).rename("CBOND_NEW_COMPOSITE_WEALTH")
    r_bond = compute_log_return(cbond_monthly, "r_bond_A")
    results["CBOND_NEW_COMPOSITE_WEALTH_月末值"] = cbond_monthly
    results["r_bond_A"] = r_bond
    print(f"\n[CBOND] 日频 {len(cbond_daily)} 条 → 月频 {len(cbond_monthly)} 条")

    # --- CBA02201.CS: 现金主腿（方案A） ---
    cba_daily = read_cba02201(RAW_DIR / "daily" / "CBA02201.CS行情数据统计明细.xls")
    cba_monthly = to_month_end(cba_daily).rename("CBA02201.CS")
    r_cash = compute_log_return(cba_monthly, "r_cash_A")
    results["CBA02201_月末值"] = cba_monthly
    results["r_cash_A"] = r_cash
    print(f"\n[CBA02201] 日频 {len(cba_daily)} 条 → 月频 {len(cba_monthly)} 条")

    # --- 合并输出 ---
    df_out = pd.DataFrame(results)
    df_out.index.name = "指标代码"
    df_out.to_csv(OUT_FILE, encoding="utf-8-sig")
    print(f"\n✓ 已保存至 {OUT_FILE}")
    print(f"  总行数: {len(df_out)}, 列数: {len(df_out.columns)}")
    print(f"  时间范围: {df_out.index[0]:%Y-%m} ~ {df_out.index[-1]:%Y-%m}")

    # --- 方案 A 收益矩阵预览 ---
    ra_cols = ["r_cash_A", "r_bond_A", "r_equity_A", "r_gold_A", "r_cmdty_A"]
    ra = df_out[ra_cols].dropna()
    print(f"\n方案 A 收益矩阵 R_A: {len(ra)} 个共同月份")
    print(f"  时间范围: {ra.index[0]:%Y-%m} ~ {ra.index[-1]:%Y-%m}")
    print("\n  60M 相关性矩阵 Corr_A(60M):")
    corr_60m = ra.tail(60).corr()
    print(corr_60m.round(3).to_string())


if __name__ == "__main__":
    main()
