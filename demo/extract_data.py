"""
demo/extract_data.py
Reads raw xlsx files and writes demo/raw_data.js for raw.html.
Run from project root: python demo/extract_data.py
"""

import json
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(__file__).parent.parent
OUT = Path(__file__).parent / "raw_data.js"


def read_choice_monthly(path: Path, col_map: dict) -> dict:
    """Read Choice-format monthly xlsx. Rows 0-2 are metadata; data from row 3."""
    df = pd.read_excel(path, sheet_name=0, header=None)
    result = {}
    for col_idx, code in col_map.items():
        dates, values = [], []
        for _, row in df.iloc[3:].iterrows():
            date_val = str(row[1]) if pd.notna(row[1]) else ""
            if len(date_val) >= 4 and date_val[:4] in ("2024", "2025", "2026"):
                label = date_val[:7] if len(date_val) >= 7 else date_val[:4]
                try:
                    v = float(row[col_idx]) if pd.notna(row[col_idx]) else None
                    dates.append(label)
                    values.append(round(v, 4) if v is not None else None)
                except (ValueError, KeyError):
                    dates.append(label)
                    values.append(None)
        result[code] = {"dates": dates, "values": values}
    return result


def read_choice_daily(path: Path, col_map: dict) -> dict:
    """Read Choice-format daily xlsx."""
    df = pd.read_excel(path, sheet_name=0, header=None)
    result = {}
    for col_idx, code in col_map.items():
        dates, values = [], []
        for _, row in df.iloc[3:].iterrows():
            if pd.isna(row[1]):
                continue
            try:
                dt = pd.to_datetime(row[1])
                if dt.year not in (2024, 2025, 2026):
                    continue
                v = float(row[col_idx]) if pd.notna(row[col_idx]) else None
                dates.append(str(dt.date()))
                values.append(round(v, 4) if v is not None else None)
            except (ValueError, TypeError):
                continue
        result[code] = {"dates": dates, "values": values}
    return result


def read_kline(path: Path, code: str) -> dict:
    """Read Choice K-line export; extract 收盘价."""
    df = pd.read_excel(path, sheet_name=0)
    df = df.dropna(subset=["交易时间", "收盘价"])
    df["交易时间"] = pd.to_datetime(df["交易时间"], errors="coerce")
    df = df[df["交易时间"].dt.year.isin([2024, 2025, 2026])]
    dates = [str(d.date()) for d in df["交易时间"]]
    values = [round(float(v), 4) for v in df["收盘价"]]
    return {code: {"dates": dates, "values": values}}


def read_annual(path: Path, col_idx: int, code: str) -> dict:
    """Read annual frequency file."""
    df = pd.read_excel(path, sheet_name=0, header=None)
    dates, values = [], []
    for _, row in df.iloc[3:].iterrows():
        date_val = str(row[1]) if pd.notna(row[1]) else ""
        if date_val[:4] in ("2024", "2025", "2026"):
            try:
                v = float(row[col_idx]) if pd.notna(row[col_idx]) else None
                dates.append(date_val[:4])
                values.append(round(v, 4) if v is not None else None)
            except (ValueError, TypeError):
                pass
    return {code: {"dates": dates, "values": values}}


def main():
    data = {}

    # ── Section 1: 宏观周期与政策环境 ─────────────────────────────────────────
    print("Section 1 ...")
    s1 = {}
    s1.update(read_choice_monthly(
        BASE / "data/raw/monthly/nbs_macro_core_20260305.xlsx",
        {2: "CPI_YOY", 3: "PPI_YOY", 4: "PMI_MANU", 5: "PMI_SERV", 6: "INDUSTRY_YOY"},
    ))
    s1.update(read_choice_monthly(
        BASE / "data/raw/monthly/macro_20260310.xlsx",
        {2: "TSF_STOCK_YOY", 3: "M2_YOY", 4: "LPR_1Y", 6: "GOV_EXPEND_CUMULATIVE_YOY"},
    ))
    s1.update(read_choice_monthly(
        BASE / "data/raw/monthly/marco_0316.xlsx",
        {2: "SPECIAL_BOND_ISSUE_CUM", 3: "RRR_LARGE_FIN_INST"},
    ))
    s1.update(read_choice_daily(
        BASE / "data/raw/daily/cn_bond_credit_rates_daily.xlsx",
        {4: "CGB_10Y", 6: "DR007"},
    ))
    s1.update(read_annual(
        BASE / "data/raw/monthly/special_bonds_annual.xlsx", 2,
        "LOCAL_SPECIAL_BOND_TARGET_ANNUAL",
    ))
    data["section1"] = s1

    # ── Section 2: 市场动能拆解 ────────────────────────────────────────────────
    print("Section 2 ...")
    data["section2"] = read_choice_monthly(
        BASE / "data/raw/monthly/growth.xlsx",
        {
            2: "RETAIL_SALES_YOY",
            3: "CONSUMER_CONFIDENCE",
            4: "MANUFACTURING_INVEST_CUM_YOY",
            5: "REAL_ESTATE_INVEST_CUM_YOY",
            6: "INFRA_INVEST_CUM_YOY",
            7: "RESID_HOUSE_SALES_CUMULATIVE_YOY",
            8: "EXPORT_CUMULATIVE_YOY",
            9: "PMI_NEW_EXPORT_ORDERS",
        },
    )

    # ── Section 3: 国际环境与跨市场映射 ──────────────────────────────────────
    print("Section 3 ...")
    data["section3"] = read_choice_daily(
        BASE / "data/raw/daily/cross_market.xlsx",
        {2: "BRENT_CRUDE", 3: "VIX", 4: "XAUUSD", 5: "FX_CNY_MID"},
    )

    # ── Section 4: 大类资产驱动与建模数据 ────────────────────────────────────
    print("Section 4 ...")
    s4 = {}
    s4.update(read_choice_monthly(
        BASE / "data/raw/monthly/cash_mmf_yld.xlsx",
        {2: "MMF_7D_YIELD_M"},
    ))
    s4.update(read_choice_daily(
        BASE / "data/raw/daily/cn_bond_credit_rates_daily.xlsx",
        {2: "CBOND_NEW_COMPOSITE_WEALTH", 3: "CGB_3Y", 5: "AA_CREDIT_YIELD_3Y"},
    ))
    s4.update(read_kline(BASE / "data/raw/daily/K线导出_H00300_日线数据.xlsx", "CSI300_TR"))
    s4.update(read_kline(BASE / "data/raw/daily/K线导出_000300_日线数据.xlsx", "CSI300"))
    s4.update(read_kline(BASE / "data/raw/daily/K线导出_AU9999_日线数据.xlsx", "AU9999"))
    s4.update(read_kline(BASE / "data/raw/daily/K线导出_NHCI_日线数据.xlsx", "NHCI"))
    data["section4"] = s4

    # Write JS file
    json_str = json.dumps(data, ensure_ascii=False)
    OUT.write_text(f"const RAW_DATA = {json_str};\n", encoding="utf-8")
    print(f"Written → {OUT}  ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
