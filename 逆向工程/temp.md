# 方案一 

## 1.  完整市场分析 prompt 

## 2. 作为提示词工程师， 如何优化？
你是一名具备金融分析、量化研究与理财规划能力的专业投资顾问。你擅长通过量化数据挖掘市场信号，并能将复杂的宏观逻辑转化为可落地的投资建议。

作为提示词工程师， 如何优化下面的提示词，让模型更好理解？ 是在金融分析、量化研究、投资顾问领域。 


作为提示词工程师， 如何优化？ 输出的时候是用户好理解的指标名字。 类似： CPI同比， PPI 同比

下面是提示词。
```
【指标说明】  

- `CPI_YOY`: 居民消费价格指数同比 (%)
- `PPI_YOY`: 工业生产者出厂价格指数同比 (%)
- `LPR_1Y`: 1年期贷款市场报价利率 (%)
- `YIELD_10Y`: 10年期国债到期收益率 (%)
- `FX_CNY_MID_MONTHLY`: 人民币兑美元中间价 (CNY/USD)
- `GOV_EXPEND_CUMULATIVE_YOY`: 政府支出累计同比 (%)
- `INDUSTRY_YOY`: 规模以上工业增加值同比 (%)
- `PMI_MANU`: 制造业采购经理指数 (Index)
- `PMI_SERV`: 服务业商务活动指数 (Index)
- `TSF_STOCK_YOY`: 社会融资存量同比 (%)

```csv
indicator_id,ref_month,value,unit,adjustment,source,data_type
CPI_YOY,2024-01,-0.8,%,YoY,NBS,Inflation
```

## 3. 这个能否再简化？

这个能否再简化？
| `indicator_id` | 极简 `display_name` |
|----------------|---------------------|
| `CPI_YOY`      | CPI同比 |
| `PPI_YOY`      | PPI同比 |
| `LPR_1Y`       | 1年期LPR |
| `YIELD_10Y`    | 10年期国债收益率 |
| `FX_CNY_MID_MONTHLY` | 人民币汇率中间价 |
| `GOV_EXPEND_CUMULATIVE_YOY` | 政府支出累计同比 |
| `INDUSTRY_YOY` | 工业增加值同比 |
| `PMI_MANU`     | 制造业PMI |
| `PMI_SERV`     | 服务业PMI |
| `TSF_STOCK_YOY` | 社融存量同比 |

# 方案二

## 1. 作为提示词工程师评估提示词。


当前宏观经济与市场环境（截至2026年1月）

【指标定义】  

- `CPI_YOY`: 居民消费价格指数同比 (%)
- `PPI_YOY`: 工业生产者出厂价格指数同比 (%)
- `LPR_1Y`: 1年期贷款市场报价利率 (%)
- `YIELD_10Y`: 10年期国债到期收益率 (%)
- `FX_CNY_MID_MONTHLY`: 人民币兑美元中间价 (CNY/USD)
- `GOV_EXPEND_CUMULATIVE_YOY`: 政府支出累计同比 (%)
- `INDUSTRY_YOY`: 规模以上工业增加值同比 (%)
- `PMI_MANU`: 制造业采购经理指数 (Index)
- `PMI_SERV`: 服务业商务活动指数 (Index)
- `TSF_STOCK_YOY`: 社会融资存量同比 (%)

```csv
indicator_id,ref_month,value,unit,adjustment,source,data_type
CPI_YOY,2024-01,-0.8,%,YoY,NBS,Inflation
CPI_YOY,2024-02,0,%,YoY,NBS,Inflation
CPI_YOY,2024-03,0,%,YoY,NBS,Inflation
``

## 2. 只需要评估这个提示词片段， indicator_id定义是否正确
