"""
extract_display_data.py
-----------------------
从 data/raw/ 原始文件提取指标展示表格所需数据，按数据采购清单v3分类输出。
- 月频/季频指标：纵向展示 2025-03 ~ 2026-03（13个月）
- 日频指标：横向展示 2026-03 每日数据（日期为列）
- 分类依据：数据采购清单v3.md
- 新指标数据来源参考：data/raw/CLAUDE.md

运行方式（从项目根目录）：
    python docs/指标确认表格/extract_display_data.py
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 项目根目录
RAW = ROOT / "data" / "raw"

MONTH_START = "2025-03"
MONTH_END = "2026-03"
DAILY_MONTH = "2026-03"


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def read_choice_monthly(path: Path, skip_rows: int = 5) -> pd.DataFrame:
    """
    读取 Choice 导出的月频 Excel。
    skiprows 跳过元数据行，之后第一行当 header，再 rename。
    非日期行由 dropna 自动过滤。
    """
    df = pd.read_excel(path, sheet_name=0, skiprows=skip_rows, header=0)
    df = df.iloc[:, 1:]  # 去掉序号列
    df.columns = ["date"] + [f"col{i}" for i in range(len(df.columns) - 1)]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    return df


def read_choice_daily(path: Path, skip_rows: int = 7) -> pd.DataFrame:
    """读取 Choice 导出的日频 Excel，返回日频 DataFrame。"""
    df = pd.read_excel(path, sheet_name=0, skiprows=skip_rows, header=0)
    df = df.iloc[:, 1:]
    df.columns = ["date"] + [f"col{i}" for i in range(len(df.columns) - 1)]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    return df


def read_kline(path: Path) -> pd.DataFrame:
    """读取 Choice K线导出 Excel（无元数据行），提取收盘价。"""
    df = pd.read_excel(path, sheet_name=0, header=0)
    df = df.rename(columns={"交易时间": "date"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    return df[["收盘价"]].rename(columns={"收盘价": "close"})


def to_period(df: pd.DataFrame) -> pd.DataFrame:
    """DatetimeIndex → PeriodIndex(M)。"""
    out = df.copy()
    out.index = out.index.to_period("M")
    return out


def monthend_agg(df: pd.DataFrame) -> pd.DataFrame:
    """日频 → 月末最后交易日值。"""
    monthly = df.resample("ME").last()
    monthly.index = monthly.index.to_period("M")
    return monthly


def filter_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """截取月频范围。"""
    idx = pd.period_range(MONTH_START, MONTH_END, freq="M")
    return df.reindex(idx)


def filter_daily(df: pd.DataFrame) -> pd.DataFrame:
    """截取 DAILY_MONTH 交易日。"""
    start = f"{DAILY_MONTH}-01"
    end = f"{DAILY_MONTH}-31"
    return df.loc[start:end]


def fmt(val, decimals: int = 1) -> str:
    """将数值格式化为字符串，NaN 输出 '—'。"""
    if pd.isna(val):
        return "—"
    if decimals == 0:
        return f"{int(val):,}"
    return f"{val:.{decimals}f}"


# ──────────────────────────────────────────────
# 1. 月频加载器
# ──────────────────────────────────────────────

def load_nbs_core() -> dict:
    """nbs_macro_core_20260305.xlsx → CPI PPI PMI_MANU PMI_SERV INDUSTRY_YOY"""
    path = RAW / "monthly" / "nbs_macro_core_20260305.xlsx"
    df = filter_monthly(to_period(read_choice_monthly(path)))
    return {
        "CPI_YOY":      df["col0"],  # EMM00072301
        "PPI_YOY":      df["col1"],  # EMM00073348
        "PMI_MANU":     df["col2"],  # EMM00121996
        "PMI_SERV":     df["col3"],  # EMM00122009
        "INDUSTRY_YOY": df["col4"],  # EMM00008445
    }


def load_macro() -> dict:
    """macro_20260310.xlsx → TSF_STOCK_YOY LPR_1Y GOV_EXPEND_CUMULATIVE_YOY"""
    path = RAW / "monthly" / "macro_20260310.xlsx"
    df = filter_monthly(to_period(read_choice_monthly(path)))
    return {
        "TSF_STOCK_YOY":             df["col0"],  # EMM00634721
        "LPR_1Y":                    df["col1"],  # EMM02326278
        # col2 = LPR_5Y（跳过，非采购项）
        "GOV_EXPEND_CUMULATIVE_YOY": df["col3"],  # EMM00058496
    }


def load_growth() -> dict:
    """growth.xlsx → 8 indicators"""
    path = RAW / "monthly" / "growth.xlsx"
    df = filter_monthly(to_period(read_choice_monthly(path)))
    return {
        "RETAIL_SALES_YOY":                 df["col0"],  # EMM00063225
        "CONSUMER_CONFIDENCE":              df["col1"],  # EMM00122031
        "MANUFACTURING_INVEST_CUM_YOY":     df["col2"],  # EMM00027220
        "REAL_ESTATE_INVEST_CUM_YOY":       df["col3"],  # EMI00120220
        "INFRA_INVEST_CUM_YOY":             df["col4"],  # EMM00597116
        "RESID_HOUSE_SALES_CUMULATIVE_YOY": df["col5"],  # EMM00877640
        "EXPORT_CUMULATIVE_YOY":            df["col6"],  # EMM00183416
        "PMI_NEW_EXPORT_ORDERS":            df["col7"],  # EMM00121999
    }


def load_marco_0316() -> dict:
    """marco_0316.xlsx → SPECIAL_BOND_ISSUE_CUM RRR_LARGE_FIN_INST"""
    path = RAW / "monthly" / "marco_0316.xlsx"
    df = filter_monthly(to_period(read_choice_monthly(path)))
    return {
        "SPECIAL_BOND_ISSUE_CUM": df["col0"],  # EMM01259587
        "RRR_LARGE_FIN_INST":     df["col1"],  # EMM01280574
    }


def load_marco_meeting_318() -> dict:
    """marco_meeting_318.xlsx → M1 M2 失业率 可支配收入 进口"""
    path = RAW / "monthly" / "marco_meeting_318.xlsx"
    df = filter_monthly(to_period(read_choice_monthly(path, skip_rows=10)))
    return {
        "M1_YOY":                           df["col0"],  # EMM00087084
        "M2_YOY":                           df["col1"],  # EMM00087086
        "URBAN_SURVEYED_UNEMPLOYMENT_RATE":  df["col2"],  # EMM00631597
        "URBAN_DISPOSABLE_INCOME_CUM_YOY":  df["col3"],  # EMM00597048
        "IMPORT_CUMULATIVE_YOY":            df["col4"],  # EMM00042521
    }


def load_housing_318() -> dict:
    """housing_318.xlsx → 30城成交面积 70城二手房价"""
    path = RAW / "monthly" / "housing_318.xlsx"
    df = filter_monthly(to_period(read_choice_monthly(path, skip_rows=10)))
    return {
        "PROPERTY_SALES_AREA_30CITIES_ROLLING12M_YOY": df["col0"],  # EMI01778652
        "HOUSE_PRICE_70CITY_SECONDHAND_YOY":            df["col1"],  # EMI01736192
    }


def load_cash_mmf_yld() -> dict:
    """cash_mmf_yld.xlsx → MMF_7D_YIELD_M"""
    path = RAW / "monthly" / "cash_mmf_yld.xlsx"
    df = filter_monthly(to_period(read_choice_monthly(path, skip_rows=10)))
    return {"MMF_7D_YIELD_M": df["col0"]}  # EMI01516342


def load_gdp() -> dict:
    """GDP.xlsx → GDP_REAL_YOY（季频，非季末月显示 —）"""
    path = RAW / "monthly" / "GDP.xlsx"
    df = filter_monthly(to_period(read_choice_monthly(path, skip_rows=10)))
    return {"GDP_REAL_YOY": df["col0"]}  # EMM00000012


# ──────────────────────────────────────────────
# 2. 日频加载器（月末聚合 + 原始日频）
# ──────────────────────────────────────────────

def load_cn_bond_daily():
    """cn_bond_credit_rates_daily.xlsx → CBOND CGB_3Y CGB_10Y AA DR007"""
    path = RAW / "daily" / "cn_bond_credit_rates_daily.xlsx"
    df = read_choice_daily(path)
    monthly = filter_monthly(monthend_agg(df))
    daily = filter_daily(df)
    m = {
        "CBOND_NEW_COMPOSITE_WEALTH": monthly["col0"],  # EMM01590538
        "CGB_3Y":                     monthly["col1"],  # E1000174
        "CGB_10Y":                    monthly["col2"],  # E1000180
        "AA_CREDIT_YIELD_3Y":         monthly["col3"],  # E1000469
        "DR007":                      monthly["col4"],  # E1300004
    }
    d = {
        "CGB_3Y":             daily["col1"],
        "CGB_10Y":            daily["col2"],
        "AA_CREDIT_YIELD_3Y": daily["col3"],
        "DR007":              daily["col4"],
    }
    return m, d


def load_bond_cgb_1y():
    """bond_CGB_1y.xlsx → CGB_1Y"""
    path = RAW / "daily" / "bond_CGB_1y.xlsx"
    df = read_choice_daily(path, skip_rows=10)
    monthly = filter_monthly(monthend_agg(df))
    daily = filter_daily(df)
    return {"CGB_1Y": monthly["col0"]}, {"CGB_1Y": daily["col0"]}  # E1000172


def load_cross_market_daily():
    """cross_market.xlsx → BRENT VIX FX_CNY_MID（gold 已拆至 gold.xlsx）"""
    path = RAW / "daily" / "cross_market.xlsx"
    df = read_choice_daily(path)
    monthly = filter_monthly(monthend_agg(df))
    daily = filter_daily(df)
    m = {
        "BRENT_CRUDE": monthly["col0"],  # EMM01588169
        "VIX":         monthly["col1"],  # EMG00002651
        "FX_CNY_MID":  monthly["col2"],  # EMM00058124
    }
    d = {
        "BRENT_CRUDE": daily["col0"],
        "VIX":         daily["col1"],
        "FX_CNY_MID":  daily["col2"],
    }
    return m, d


def load_gold_daily():
    """gold.xlsx → XAUUSD"""
    path = RAW / "daily" / "gold.xlsx"
    df = read_choice_daily(path, skip_rows=10)
    monthly = filter_monthly(monthend_agg(df))
    daily = filter_daily(df)
    return {"XAUUSD": monthly["col0"]}, {"XAUUSD": daily["col0"]}  # EMI01778678


def load_kline_all():
    """K线导出 → CSI300_TR CSI300 AU9999 NHCI"""
    files = {
        "CSI300_TR": RAW / "daily" / "K线导出_H00300_日线数据.xlsx",
        "CSI300":    RAW / "daily" / "K线导出_000300_日线数据.xlsx",
        "AU9999":    RAW / "daily" / "K线导出_AU9999_日线数据.xlsx",
        "NHCI":      RAW / "daily" / "K线导出_NHCI_日线数据.xlsx",
    }
    m, d = {}, {}
    for code, path in files.items():
        df = read_kline(path)
        monthly = filter_monthly(monthend_agg(df))
        daily = filter_daily(df)
        m[code] = monthly["close"]
        d[code] = daily["close"]
    return m, d


# ──────────────────────────────────────────────
# 3. 指标元信息
# ──────────────────────────────────────────────

# (显示名称, Choice ID, 数据来源, 小数位数)
INDICATOR_META = {
    "GDP_REAL_YOY":          ("中国:GDP:不变价:当季同比", "EMM00000012", "NBS", 1),
    "PMI_MANU":              ("中国:PMI", "EMM00121996", "NBS", 1),
    "PMI_SERV":              ("中国:非制造业PMI:商务活动", "EMM00122009", "NBS", 1),
    "INDUSTRY_YOY":          ("中国:工业增加值:同比", "EMM00008445", "NBS", 1),
    "CPI_YOY":               ("中国:CPI:同比", "EMM00072301", "NBS", 1),
    "PPI_YOY":               ("中国:PPI:全部工业品:同比", "EMM00073348", "NBS", 1),
    "RETAIL_SALES_YOY":      ("社会消费品零售总额:累计同比", "EMM00063225", "NBS", 1),
    "URBAN_DISPOSABLE_INCOME_CUM_YOY": ("城镇居民人均可支配收入:累计同比", "EMM00597048", "NBS", 1),
    "CONSUMER_CONFIDENCE":   ("中国:消费者信心指数", "EMM00122031", "NBS", 1),
    "INFRA_INVEST_CUM_YOY":  ("基础设施投资(不含电力):累计同比", "EMM00597116", "NBS", 1),
    "MANUFACTURING_INVEST_CUM_YOY": ("制造业投资:累计同比", "EMM00027220", "NBS", 1),
    "REAL_ESTATE_INVEST_CUM_YOY": ("房地产开发投资:累计同比", "EMI00120220", "NBS", 1),
    "RESID_HOUSE_SALES_CUMULATIVE_YOY": ("商品房销售额:住宅:累计同比", "EMM00877640", "NBS", 1),
    "PROPERTY_SALES_AREA_30CITIES_ROLLING12M_YOY": ("30大中城市商品房成交面积:当月值（万平方米）", "EMI01778652", "Choice", 1),
    "HOUSE_PRICE_70CITY_SECONDHAND_YOY": ("70城二手住宅价格指数:当月同比", "EMI01736192", "NBS", 1),
    "EXPORT_CUMULATIVE_YOY": ("出口金额:累计同比", "EMM00183416", "海关总署", 1),
    "IMPORT_CUMULATIVE_YOY": ("进口金额:累计同比", "EMM00042521", "海关总署", 1),
    "PMI_NEW_EXPORT_ORDERS": ("中国:PMI:新出口订单", "EMM00121999", "NBS", 1),
    "FX_CNY_MID":            ("中间价:美元兑人民币", "EMM00058124", "PBOC", 4),
    "M2_YOY":                ("中国:M2:同比", "EMM00087086", "PBOC", 1),
    "M1_YOY":                ("中国:M1:同比", "EMM00087084", "PBOC", 1),
    "DR007":                 ("DR007", "E1300004", "CFETS", 4),
    "TSF_STOCK_YOY":         ("社会融资规模存量:同比", "EMM00634721", "PBOC", 1),
    "AA_CREDIT_YIELD_3Y":    ("AA级信用债收益率:3年", "E1000469", "中债", 4),
    "CGB_1Y":                ("中债国债到期收益率:1年", "E1000172", "中债", 4),
    "CGB_10Y":               ("中债国债到期收益率:10年", "E1000180", "中债", 4),
    "CGB_3Y":                ("中债国债到期收益率:3年", "E1000174", "中债", 4),
    "LPR_1Y":                ("贷款市场报价利率(LPR):1年", "EMM02326278", "PBOC", 1),
    "RRR_LARGE_FIN_INST":    ("存款准备金率:大型存款类金融机构", "EMM01280574", "PBOC", 1),
    "URBAN_SURVEYED_UNEMPLOYMENT_RATE": ("城镇调查失业率", "EMM00631597", "NBS", 1),
    "GOV_EXPEND_CUMULATIVE_YOY": ("财政预算支出:累计同比", "EMM00058496", "MOF", 1),
    "SPECIAL_BOND_ISSUE_CUM": ("新增专项债券:累计值（亿元）", "EMM01259587", "MOF", 0),
    "BRENT_CRUDE":           ("ICE布油期货收盘价(连续)", "EMM01588169", "ICE", 2),
    "XAUUSD":                ("COMEX黄金期货收盘价(连续)", "EMI01778678", "COMEX", 1),
    "VIX":                   ("标准普尔500波动率指数(VIX)", "EMG00002651", "CBOE", 2),
    "MMF_7D_YIELD_M":        ("货币市场基金月均七日年化收益率", "EMI01516342", "基金业协会", 4),
    "CBOND_NEW_COMPOSITE_WEALTH": ("中债新综合财富指数(月末值)", "EMM01590538", "中债", 4),
    "CSI300_TR":             ("沪深300全收益(收盘价)", "H00300", "中证", 2),
    "CSI300":                ("沪深300(收盘价)", "000300", "中证", 2),
    "AU9999":                ("黄金9999(收盘价)", "AU9999", "上金所", 2),
    "NHCI":                  ("南华商品指数(收盘价)", "NHCI", "南华期货", 2),
}

# v3 分类结构：section → (title, [(subsection_title, [codes], is_daily_横向)])
SECTIONS = [
    ("1. 经济增长与景气", [
        ("1.1 总量", ["GDP_REAL_YOY"], False),
        ("1.2 景气度", ["PMI_MANU", "PMI_SERV"], False),
        ("1.3 工业与生产", ["INDUSTRY_YOY"], False),
    ]),
    ("2. 通胀与价格", [
        (None, ["CPI_YOY", "PPI_YOY"], False),
    ]),
    ("3. 消费与居民部门", [
        (None, ["RETAIL_SALES_YOY", "URBAN_DISPOSABLE_INCOME_CUM_YOY",
                "CONSUMER_CONFIDENCE"], False),
    ]),
    ("4. 投资与房地产", [
        ("4.1 投资", ["INFRA_INVEST_CUM_YOY", "MANUFACTURING_INVEST_CUM_YOY",
                      "REAL_ESTATE_INVEST_CUM_YOY"], False),
        ("4.2 房地产", ["RESID_HOUSE_SALES_CUMULATIVE_YOY",
                        "PROPERTY_SALES_AREA_30CITIES_ROLLING12M_YOY",
                        "HOUSE_PRICE_70CITY_SECONDHAND_YOY"], False),
    ]),
    ("5. 外需、贸易与汇率", [
        ("月频", ["EXPORT_CUMULATIVE_YOY", "IMPORT_CUMULATIVE_YOY",
                  "PMI_NEW_EXPORT_ORDERS"], False),
        ("日频", ["FX_CNY_MID"], True),
    ]),
    ("6. 货币、信用与利率", [
        ("6.1 货币（月频）", ["M2_YOY", "M1_YOY"], False),
        ("6.2 信用（月频）", ["TSF_STOCK_YOY"], False),
        ("6.3 利率与政策工具（月频）", ["LPR_1Y", "RRR_LARGE_FIN_INST"], False),
        ("日频", ["DR007", "CGB_1Y", "CGB_3Y", "CGB_10Y",
                  "AA_CREDIT_YIELD_3Y"], True),
    ]),
    ("7. 财政与就业", [
        ("7.1 就业", ["URBAN_SURVEYED_UNEMPLOYMENT_RATE"], False),
        ("7.2 财政与专项债", ["GOV_EXPEND_CUMULATIVE_YOY",
                              "SPECIAL_BOND_ISSUE_CUM"], False),
    ]),
    ("8. 国际市场与风险偏好", [
        ("日频", ["BRENT_CRUDE", "XAUUSD", "VIX"], True),
    ]),
    ("9. 大类资产建模数据", [
        ("月频", ["MMF_7D_YIELD_M", "CBOND_NEW_COMPOSITE_WEALTH"], False),
        ("日频", ["CSI300_TR", "CSI300", "AU9999", "NHCI"], True),
    ]),
]


# ──────────────────────────────────────────────
# 4. Markdown 生成
# ──────────────────────────────────────────────

def build_monthly_table(codes, monthly_data):
    """生成月频 Markdown 表格（日期为列，newest first）。"""
    periods = pd.period_range(MONTH_START, MONTH_END, freq="M")[::-1]
    col_labels = [p.strftime("%y-%m") for p in periods]

    header = "| 指标名称 | 数据来源 | Choice ID | " + " | ".join(col_labels) + " |"
    sep = "|---|---|---|" + "|".join(["---"] * len(col_labels)) + "|"
    rows = [header, sep]

    for code in codes:
        series = monthly_data.get(code)
        meta = INDICATOR_META[code]
        name, cid, source, decimals = meta
        vals = []
        for p in periods:
            v = series.get(p) if series is not None else None
            vals.append(fmt(v, decimals))
        rows.append(f"| {name} | {source} | {cid} | " + " | ".join(vals) + " |")

    return "\n".join(rows)


def build_daily_table(codes, daily_data):
    """生成日频横向 Markdown 表格（日期为列）。"""
    # 收集所有日期（取并集）
    all_dates = set()
    for code in codes:
        s = daily_data.get(code)
        if s is not None:
            all_dates.update(s.index.tolist())
    if not all_dates:
        return "> 暂无日频数据。"
    all_dates = sorted(all_dates)
    date_labels = [d.strftime("%m-%d") for d in all_dates]

    header = "| 指标名称 | Choice ID | " + " | ".join(date_labels) + " |"
    sep = "|---|---|" + "|".join(["---"] * len(date_labels)) + "|"
    rows = [header, sep]

    for code in codes:
        meta = INDICATOR_META[code]
        name, cid, _, decimals = meta
        series = daily_data.get(code)
        vals = []
        for d in all_dates:
            v = series.get(d) if series is not None else None
            vals.append(fmt(v, decimals))
        rows.append(f"| {name} | {cid} | " + " | ".join(vals) + " |")

    return "\n".join(rows)


def generate_markdown(monthly_data, daily_data):
    """生成完整 Markdown。"""
    lines = []
    lines.append("# 指标展示表格")
    lines.append("")
    lines.append(
        f"> **月频时间范围**：{MONTH_START} ~ {MONTH_END}"
        f" &emsp;**日频**：展示 {DAILY_MONTH} 每日数据"
        f" &emsp;**更新日期**：2026-03-19"
    )
    lines.append(">")
    lines.append("> — 表示当期数据未发布、文件未覆盖或市场休市。")
    lines.append(">")
    lines.append(
        "> 数据来源文件见 [data/raw/CLAUDE.md](../../data/raw/CLAUDE.md)"
        " | 指标分类依据 [数据采购清单v3.md](../数据采购清单v3.md)"
    )
    lines.append("")

    for section_title, subsections in SECTIONS:
        lines.append("---")
        lines.append("")
        lines.append(f"## {section_title}")
        lines.append("")

        for sub_title, codes, is_daily in subsections:
            if sub_title:
                lines.append(f"### {sub_title}")
                lines.append("")
            if is_daily:
                lines.append(f"> 日频横向展示（{DAILY_MONTH}）")
                lines.append("")
                lines.append(build_daily_table(codes, daily_data))
            else:
                lines.append(build_monthly_table(codes, monthly_data))
            lines.append("")

    # 附注
    lines.append("---")
    lines.append("")
    lines.append("## 附注")
    lines.append("")
    lines.append("- `GDP_REAL_YOY`：季频指标，仅季末月（3/6/9/12月）有值，其余月份为 —。")
    lines.append("- `URBAN_DISPOSABLE_INCOME_CUM_YOY`：季频指标，同上。")
    lines.append("- `INDUSTRY_YOY`：1月、2月不单独发布，随1-2月合并数据发布。")
    lines.append("- `RETAIL_SALES_YOY` 等累计同比指标：1月数据随1-2月合并数据发布。")
    lines.append("- `LOCAL_SPECIAL_BOND_TARGET_ANNUAL`（年频）不纳入月度展示表。")
    lines.append("- 日频数据截止日期取决于文件导出时间，可能不包含月末全部交易日。")
    lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────

def main():
    print("读取原始文件...")

    # --- 月频 ---
    monthly_data: dict[str, pd.Series] = {}
    monthly_data.update(load_nbs_core())
    monthly_data.update(load_macro())
    monthly_data.update(load_growth())
    monthly_data.update(load_marco_0316())
    monthly_data.update(load_marco_meeting_318())
    monthly_data.update(load_housing_318())
    monthly_data.update(load_cash_mmf_yld())
    monthly_data.update(load_gdp())

    # --- 日频（月末聚合 → monthly_data；原始 → daily_data）---
    daily_data: dict[str, pd.Series] = {}

    cn_bond_m, cn_bond_d = load_cn_bond_daily()
    monthly_data.update(cn_bond_m)
    daily_data.update(cn_bond_d)

    cgb1y_m, cgb1y_d = load_bond_cgb_1y()
    monthly_data.update(cgb1y_m)
    daily_data.update(cgb1y_d)

    cross_m, cross_d = load_cross_market_daily()
    monthly_data.update(cross_m)
    daily_data.update(cross_d)

    gold_m, gold_d = load_gold_daily()
    monthly_data.update(gold_m)
    daily_data.update(gold_d)

    kline_m, kline_d = load_kline_all()
    monthly_data.update(kline_m)
    daily_data.update(kline_d)

    # --- 生成 Markdown ---
    md = generate_markdown(monthly_data, daily_data)
    out_path = Path(__file__).resolve().parent / "指标展示表格.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"已写入 {out_path}")

    # 汇总统计
    m_count = sum(1 for k, v in monthly_data.items() if v is not None and v.notna().any())
    d_count = sum(1 for k, v in daily_data.items() if v is not None and v.notna().any())
    print(f"月频指标（含日频月末聚合）：{m_count} 个")
    print(f"日频指标（{DAILY_MONTH}）：{d_count} 个")


if __name__ == "__main__":
    main()
