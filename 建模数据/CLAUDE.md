# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

四大类资产建模数据加工目录。从 `建模月频序列.csv` 出发，计算月收益率、多窗口统计量（相关性、协方差、波动率、预期收益）和无风险利率基准，输出供 MVO / Black-Litterman 组合优化使用的完整参数集。

## Two Modeling Schemes

- **方案 A (Total Return)**：正式配置主矩阵。4 条资产腿（现金 / 固收 / 股票 / 另类），收益率口径，所有脚本已实现。
- **方案 B (Price Factor)**：解释型因子矩阵（股票价格、利率变化、信用利差变化、黄金、商品），用于风险归因。尚未实现脚本。

方案 A 与方案 B 不混用同一套收益/因子矩阵。

## 4 Asset Legs (Plan A)

| 代号 | 原始指标 | 说明 |
|------|----------|------|
| r_cash | CBA02201.CS | 中债货币市场基金可投资债券财富(总值)指数 |
| r_bond | CBOND_NEW_COMPOSITE_WEALTH | 中债新综合指数(财富指数) |
| r_equity | CSI300_TR | 沪深300全收益指数 |
| r_alt | 0.7 × AU9999 + 0.3 × NHCI | 70%黄金 + 30%商品合成 |

收益率：简单月收益率 `P_t / P_{t-1} - 1`。年化：`μ × 12`，`σ × √12`，`Σ × 12`。

## Data Flow

```
建模月频序列.csv  (10 indicators, month-end values, 2002-01~)
        │
        ├─→ cgb_rate_analysis.py       → cgb_summary_metrics.csv（季末利率与期限利差）
        │
        ├─→ plan_a_modeling.py         → plan_a_returns.csv（4腿月收益率）
        │                              → plan_a_windows/{corr,cov,sigma,mu}_{W}M.csv
        │
        └─→ asset_benchmark_profile.py → asset_benchmark_profile.csv（4资产基准画像）
              ↑ 读取 plan_a_returns.csv + 建模月频序列.csv 的 CGB_1Y
```

## Commands

```bash
# 从项目根目录运行（有依赖顺序：先 plan_a_modeling → 再 asset_benchmark_profile）
python3 建模数据/plan_a_modeling.py            # 方案A全量：月收益 + 6窗口统计
python3 建模数据/cgb_rate_analysis.py          # 国债收益率季末序列 + 期限利差
python3 建模数据/asset_benchmark_profile.py    # 4资产基准画像（年化收益/波动率/Sharpe）
python3 建模数据/demo_modeling_data.py         # Choice导出格式解析demo
```

## Key Rules

- 日频→月频统一取**月末值**；月末无报价则取该月最后有效交易日
- 整月缺失**不做机械插值**，相关性计算用窗口内共同有效样本
- 计算窗口：12M, 24M, 36M, 60M, 120M, 240M（代码中实际使用；设计文档还包含 180M）
- 瓶颈列 CBA02201.CS 起始于 2005-07，4 腿收益最早可算 2005-08
- 无风险利率 `rf` 基于 CGB_1Y 多窗口均值；长端锚 `long_rate` 基于 CGB_10Y
- 样本不足窗口要求时输出 NaN，不补值
- 计算过程保留原始精度，仅最终输出 round

## Output Structure

- `plan_a_returns.csv` — 4 列月收益率时间序列（r_cash / r_bond / r_equity / r_alt）
- `plan_a_corr_mu.csv` — 各窗口相关性与预期收益（long format）
- `plan_a_windows/` — 每窗口 4 个文件：`corr_WM.csv`, `cov_WM.csv`, `sigma_WM.csv`, `mu_WM.csv`
- `cgb_summary_metrics.csv` — 季末 CGB_1Y / CGB_10Y / term_spread 序列（2021Q1 起）
- `asset_benchmark_profile.csv` — 4 资产 × {ann_return, ann_vol, sharpe_ratio} × {1Y, 3Y, 5Y}

## Database Target Schema (Planned)

1 张数学建模核心表，5 个核心变量：
1. `asset_volatility_sigma` — 单资产年化波动率
2. `asset_covariance_matrix_sigma` — 年化协方差矩阵
3. `asset_correlation_matrix_rho` — 相关性矩阵
4. `risk_free_rate_rf` — 无风险利率
5. `asset_benchmark_profile` — 收益/波动/Sharpe 画像
