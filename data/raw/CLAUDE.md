# data/raw — 原始文件索引

> **废弃目录**：`deprecated/` 内文件不参与任何 ETL 处理，忽略即可。
>
> **重叠处理**：同一指标出现在多个文件时，以**数据截止日期最晚**的文件为准。
> 文件名中的 `YYYYMMDD` 是**导出日期**，不是数据截止日期；截止日期见下表。

---

## 指标 → 文件 对照表

### monthly/

| 指标代码 | Choice ID | 指标名称（Choice 原名） | 数据范围 | 来源文件 |
|---|---|---|---|---|
| CPI_YOY | EMM00072301 | 中国:CPI:同比 | 2006-01 ~ 2026-02 | `nbs_macro_core_20260305.xlsx` |
| PPI_YOY | EMM00073348 | 中国:PPI:全部工业品:同比 | 2006-01 ~ 2026-02 | `nbs_macro_core_20260305.xlsx` |
| PMI_MANU | EMM00121996 | 中国:PMI | 2006-01 ~ 2026-02 | `nbs_macro_core_20260305.xlsx` |
| PMI_SERV | EMM00122009 | 中国:非制造业PMI:商务活动 | 2006-01 ~ 2026-02 | `nbs_macro_core_20260305.xlsx` |
| INDUSTRY_YOY | EMM00008445 | 中国:工业增加值:同比 | 2006-01 ~ 2026-02 | `nbs_macro_core_20260305.xlsx` |
| TSF_STOCK_YOY | EMM00634721 | 中国:社会融资规模存量:同比 | 1951-12 ~ 2026-02 | `macro_20260310.xlsx` |
| LPR_1Y | EMM02326278 | 贷款市场报价利率(LPR):1年 | 1951-12 ~ 2026-02 | `macro_20260310.xlsx` |
| GOV_EXPEND_CUMULATIVE_YOY | EMM00058496 | 中国:财政预算支出:累计同比 | 1951-12 ~ 2026-02 | `macro_20260310.xlsx` |
| M1_YOY | EMM00087084 | 中国:M1:同比 | 1953-12 ~ 2026-02 | `marco_meeting_318.xlsx` |
| M2_YOY | EMM00087086 | 中国:M2:同比 | 1953-12 ~ 2026-02 | `marco_meeting_318.xlsx` |
| URBAN_SURVEYED_UNEMPLOYMENT_RATE | EMM00631597 | 中国:城镇调查失业率 | 1953-12 ~ 2026-02 | `marco_meeting_318.xlsx` |
| URBAN_DISPOSABLE_INCOME_CUM_YOY | EMM00597048 | 中国:城镇居民人均可支配收入:实际累计同比 | 1953-12 ~ 2026-02 | `marco_meeting_318.xlsx` |
| IMPORT_CUMULATIVE_YOY | EMM00042521 | 中国:进口金额:累计同比 | 1953-12 ~ 2026-02 | `marco_meeting_318.xlsx` |
| EXPORT_AMOUNT_YOY | EMM00183406 | 中国:出口金额:同比 | 2014-01 ~ 2026-02 | `import_export.xlsx` |
| IMPORT_AMOUNT_YOY | EMM00183407 | 中国:进口金额:同比 | 2014-01 ~ 2026-02 | `import_export.xlsx` |
| SPECIAL_BOND_ISSUE_CUM | EMM01259587 | 中国:发行地方政府债券:…发行新增专项债券:累计值 | 1999-11 ~ 2026-02 | `marco_0316.xlsx` |
| RRR_LARGE_FIN_INST | EMM01280574 | 中国:人民币存款准备金率:大型存款类金融机构(月) | 1999-11 ~ 2026-02 | `marco_0316.xlsx` |
| LOCAL_SPECIAL_BOND_TARGET_ANNUAL | EMM01430555 | 中国:政府预期目标:地方专项债 | 2016 ~ 2026 | `special_bonds_annual.xlsx` |
| RETAIL_SALES_YOY | EMM00063225 | 中国:社会消费品零售总额:累计同比 | 1992-02 ~ 2026-02 | `growth.xlsx` |
| CONSUMER_CONFIDENCE | EMM00122031 | 中国:消费者信心指数 | 1992-02 ~ 2026-02 | `growth.xlsx` |
| MANUFACTURING_INVEST_CUM_YOY | EMM00027220 | 中国:固定资产投资完成额:制造业:累计同比 | 1992-02 ~ 2026-02 | `growth.xlsx` |
| REAL_ESTATE_INVEST_CUM_YOY | EMI00120220 | 中国:房地产开发投资完成额:累计同比 | 1992-02 ~ 2026-02 | `growth.xlsx` |
| INFRA_INVEST_CUM_YOY | EMM00597116 | 中国:城镇固定资产投资完成额:基础设施(不含电力):累计同比 | 1992-02 ~ 2026-02 | `growth.xlsx` |
| RESID_HOUSE_SALES_CUMULATIVE_YOY | EMM00877640 | 商品房销售额:住宅:累计同比 | 1992-02 ~ 2026-02 | `growth.xlsx` |
| EXPORT_CUMULATIVE_YOY | EMM00183416 | 中国:出口金额:累计同比 | 1992-02 ~ 2026-02 | `growth.xlsx` |
| PMI_NEW_EXPORT_ORDERS | EMM00121999 | 中国:PMI:新出口订单 | 1992-02 ~ 2026-02 | `growth.xlsx` |
| MMF_7D_YIELD_M | EMI01516342 | 中国货币市场基金月平均七日年化收益率 | 2004-01 ~ 2026-03 | `cash_mmf_yld.xlsx` |
| GDP_REAL_YOY | EMM00000012 | 中国:GDP:不变价:同比 | 1993-03 ~ 2025-12 | `GDP.xlsx` |
| PROPERTY_SALES_AREA_30CITIES_ROLLING12M_YOY | EMI01778652 | 中国:30大中城市:商品房成交面积:当月值 | 2006-01 ~ 2026-02 | `housing_318.xlsx` |
| HOUSE_PRICE_70CITY_SECONDHAND_YOY | EMI01736192 | 70个大中城市:二手住宅价格指数:当月同比 | 2006-01 ~ 2026-02 | `housing_318.xlsx` |

### daily/

| 指标代码 | Choice ID | 指标名称（Choice 原名） | 数据范围 | 来源文件 |
|---|---|---|---|---|
| CBOND_NEW_COMPOSITE_WEALTH | EMM01590538 | 中债新综合指数 | 2002-01-04 ~ 2026-03-16 | `cn_bond_credit_rates_daily.xlsx` |
| CGB_3Y | E1000174 | 中债国债到期收益率:3年 | 2002-01-04 ~ 2026-03-16 | `cn_bond_credit_rates_daily.xlsx` |
| CGB_10Y | E1000180 | 中债国债到期收益率:10年 | 2002-01-04 ~ 2026-03-16 | `cn_bond_credit_rates_daily.xlsx` |
| AA_CREDIT_YIELD_3Y | E1000469 | 中债企业债到期收益率(AA):3年 | 2002-01-04 ~ 2026-03-16 | `cn_bond_credit_rates_daily.xlsx` |
| DR007 | E1300004 | DR007 | 2002-01-04 ~ 2026-03-16 | `cn_bond_credit_rates_daily.xlsx` |
| CGB_1Y | E1000172 | 中债国债到期收益率:1年 | 2002-01-04 ~ 2026-03-18 | `bond_CGB_1y.xlsx` |
| BRENT_CRUDE | EMM01588169 | 期货收盘价(连续):ICE布油 | 1975-01-02 ~ 2026-03-16 | `cross_market.xlsx` |
| VIX | EMG00002651 | 标准普尔500波动率指数(VIX) | 1975-01-02 ~ 2026-03-16 | `cross_market.xlsx` |
| FX_CNY_MID | EMM00058124 | 中间价:美元兑人民币 | 1975-01-02 ~ 2026-03-16 | `cross_market.xlsx` |
| XAUUSD | EMI01778678 | 期货收盘价(连续):COMEX黄金 | 1986-07-01 ~ 2026-03-17 | `gold.xlsx` |
| CSI300_TR | H00300 | 沪深300全收益（收盘价列） | 2004-12-31 ~ 2026-03-16 | `K线导出_H00300_日线数据.xlsx` |
| CSI300 | 000300 | 沪深300（收盘价列） | 2005-01-04 ~ 2026-03-17 | `K线导出_000300_日线数据.xlsx` |
| AU9999 | AU9999 | 黄金9999（上金所，收盘价列） | 2004-01-02 ~ 2026-03-17 | `K线导出_AU9999_日线数据.xlsx` |
| NHCI | NHCI | 南华商品指数（收盘价列） | 2004-06-01 ~ 2026-03-17 | `K线导出_NHCI_日线数据.xlsx` |
| CBA02201.CS | CBA02201.CS | 中债货币市场基金可投资债券财富(总值)指数（收盘价列） | 2005-07-04 ~ 2026-03-19 | `CBA02201.CS行情数据统计明细.xls` |

---

## 文件备注

### monthly/

| 文件 | 说明 |
|---|---|
| `nbs_macro_core_20260305.xlsx` | NBS 核心 5 指标；按月导出，文件名后缀为导出日期 |
| `macro_20260310.xlsx` | PBOC / MOF 3 指标；含额外列 LPR_5Y（EMM02326279），ETL 跳过 |
| `marco_meeting_318.xlsx` | 3/18 补充批次，PBOC / NBS / 海关 5 指标；含额外列 EMM00087129（各项贷款余额:同比）、EMM00088685（社会融资增量:新增人民币贷款），ETL 跳过 |
| `marco_0316.xlsx` | 财政部 / PBOC 2 指标 |
| `special_bonds_annual.xlsx` | 年频；单列，稳定无需频繁更新 |
| `growth.xlsx` | NBS / 海关 8 指标合并文件（由旧版 nbs_macro_noncore + growth_momentum 整合而来） |
| `cash_mmf_yld.xlsx` | 月频；货基 7 日年化收益率，截止当月 |
| `GDP.xlsx` | 季频；仅 GDP_REAL_YOY 一列，截止上季度末 |
| `housing_318.xlsx` | 3/18 补充批次，房地产高频成交与房价 2 指标 |
| `import_export.xlsx` | 海关总署；出口/进口金额**当月**同比（EMM00183406 / EMM00183407）；与 `growth.xlsx` 的累计同比（EXPORT_CUMULATIVE_YOY / IMPORT_CUMULATIVE_YOY）及 `marco_meeting_318.xlsx` 的进口累计同比为不同口径，不视为同一指标重叠 |
| `nbs_macro_noncore_20260309.xlsx` | ⚠️ 旧版文件，使用已废弃的 Choice ID；**已被 `growth.xlsx` 完全取代，不得用于 ETL** |

### daily/

| 文件 | 说明 |
|---|---|
| `cn_bond_credit_rates_daily.xlsx` | 中债 / 货币网 5 指标；同时写入 `macro_daily`（日频）和 `macro_monthly`（月均聚合） |
| `bond_CGB_1y.xlsx` | 仅 CGB_1Y 一列；截止日期比 cn_bond_credit_rates_daily.xlsx 略新 |
| `cross_market.xlsx` | ICE 布油 / VIX / 美元兑人民币 3 指标；VIX 路由至 `market_daily`，其余路由至 `macro_daily` |
| `gold.xlsx` | COMEX 黄金期货收盘价（连续合约）；2026-03-16 从 cross_market.xlsx 拆出独立文件 |
| `K线导出_*.xlsx` | Choice K线导出格式（含开高低收量）；ETL **只提取收盘价列**，写入 `quant_daily` |
| `CBA02201.CS行情数据统计明细.xls` | 中债货币市场基金可投资债券财富(总值)指数；Choice 行情导出格式，ETL **只提取收盘价列**；方案A现金主腿 |

### deprecated/（不处理）

`VIX.xlsx` · `china_bond.xlsx` · `gdp_quarter.xlsx` · `growth_momentum.xlsx` · `market_1.xlsx` · `oil.xlsx` · `rates.xlsx` · `公开市场操作.xlsx`
