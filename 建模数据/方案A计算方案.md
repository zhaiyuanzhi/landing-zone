# 方案A 大类资产建模数据加工（4条资产腿）

## 定位

方案A（Total Return 投资回报口径）用于正式配置主矩阵，服务组合优化、风险预算、长期回测、Black-Litterman / MVO。

## 数据来源

- 月频原始数据：`建模月频序列.csv`（已统一月末值）
- 无风险利率：`cgb_summary_metrics.csv`（已计算完毕）

## 4条资产腿定义

| 资产腿 | 代号 | 原始指标 | 说明 |
|--------|------|----------|------|
| 现金 | r_cash | CBA02201.CS | 中债货币市场基金可投资债券财富(总值)指数 |
| 固收 | r_bond | CBOND_NEW_COMPOSITE_WEALTH | 中债新综合指数(财富指数) |
| 股票 | r_equity | CSI300_TR | 沪深300全收益指数 |
| 另类 | r_alt | 0.7 × AU9999 + 0.3 × NHCI | 70%黄金 + 30%商品合成 |

## 月收益率计算

```text
r_cash_t   = CBA02201.CS_t / CBA02201.CS_{t-1} - 1
r_bond_t   = CBOND_NEW_COMPOSITE_WEALTH_t / CBOND_NEW_COMPOSITE_WEALTH_{t-1} - 1
r_equity_t = CSI300_TR_t / CSI300_TR_{t-1} - 1
r_gold_t   = AU9999_t / AU9999_{t-1} - 1
r_cmdty_t  = NHCI_t / NHCI_{t-1} - 1

r_alt_t    = 0.7 × r_gold_t + 0.3 × r_cmdty_t
```

收益矩阵：`R_A,t = [r_cash_t, r_bond_t, r_equity_t, r_alt_t]`

## 多窗口计算

窗口：12M, 24M, 36M, 60M, 120M, 180M, 240M

对每个窗口 W，取最近 W 个月的收益率，计算：

- **相关性矩阵** `Corr_A(W)`：4×4，共同有效样本
- **预期收益** `μ_A(W)`：月均收益向量
- **年化预期收益** `μ_A,annual(W) = 12 × μ_A,monthly(W)`

## 无风险利率

已在 `cgb_summary_metrics.csv` 中计算：

```text
rf_current, rf_1y, rf_3y, rf_5y, rf_10y, rf_20y
long_rate_current, long_rate_1y, long_rate_3y, long_rate_5y, long_rate_10y, long_rate_20y
```

## 数据可用性

- 瓶颈列：CBA02201.CS（2005-07起）→ 收益率最早可算 2005-08
- 共同可用收益率：2005-08 ~ 2026-03，约248个月
- 最大窗口240M需要240个月 → 满足

## 输出文件

- `plan_a_returns.csv`：4条腿月收益率序列
- `plan_a_corr_mu.csv`：各窗口相关性矩阵与预期收益
