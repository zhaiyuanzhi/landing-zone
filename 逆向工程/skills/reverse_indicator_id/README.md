# Reverse Indicator ID Skill

批量逆向工程宏观/市场指标代码：给定中文指标信息，通过 Qwen 235B 推理出最合适的英文 `indicator_id`。

## 核心机制：两轮独立推理 + 一致性校验

### 为什么要两轮？

单次模型输出可能受 prompt 措辞、采样随机性影响。两轮独立调用（Round 1 和 Round 2 使用不同系统 prompt、完全独立的上下文）可以验证命名建议的稳定性：

- **Round 1**：完整推理，输出推荐 ID + 备选 + 命名理由
- **Round 2**：新上下文，仅输出推荐 ID + 备选（不带 Round 1 结果）
- **比较**：两轮结果一致性 → high / medium / low

如果两轮独立给出相同答案，该命名的可信度显著提升。

### 一致性等级详解

| 等级 | 符号 | 判定条件 | 含义 | 处理方式 |
|------|------|----------|------|----------|
| **high** | ✓ | 两轮结果完全一致，或经缩写等价映射后一致（如 `MANU` = `MANUFACTURING`），或仅差一个可选修饰词（如 `CGB_3Y` vs `CGB_YTM_3Y`，`YIELD` 在上下文中已隐含） | 模型在独立上下文中给出了相同的命名判断，说明该 indicator_id 是金融语境下的"自然选择"，具备高可复现性 | 直接采用，无需人工复核 |
| **medium** | ~ | 两轮结果主干一致但有细微差异：token 重叠度 ≥ 60%（Jaccard），或其中一个是另一个的子串，或一轮的推荐出现在另一轮的备选列表中 | 模型对核心语义的理解一致，但在缩写程度、是否加后缀等"风格"层面存在分歧。例如 `CONSUMER_CONFIDENCE` vs `CONSUMER_CONFIDENCE_INDEX` | 程序自动择优（优先选更简洁、confidence 更高的），但建议人工确认 |
| **low** | ✗ | 两轮结果差异显著：token 重叠度 < 60%，不存在子串关系，也没有交叉备选命中 | 模型对该指标的命名没有形成稳定共识，可能是指标本身语义模糊、或 prompt 信息不足 | **必须人工复核**，不应直接采用 |

#### 缩写等价映射（comparator 内置）

以下缩写对在比较时视为等价，不会降低一致性等级：

| 缩写 | 等价全称 | 示例 |
|------|----------|------|
| MANU | MANUFACTURING | `MANU_INVEST_CUM_YOY` = `MANUFACTURING_INVEST_CUM_YOY` |
| INFRA | INFRASTRUCTURE | `INFRA_INVEST` = `INFRASTRUCTURE_INVEST` |
| INVEST | INVESTMENT | `MANU_INVEST` = `MANU_INVESTMENT` |
| GOV | GOVERNMENT | `GOV_EXPEND` = `GOVERNMENT_EXPEND` |
| CUM | CUMULATIVE | `EXPORT_CUM` = `EXPORT_CUMULATIVE` |
| YTM | YIELD | `CGB_YTM_3Y` = `CGB_YIELD_3Y` |

#### 可选修饰词（差一个也算 high）

当两轮结果在 canonicalize 后仅差一个以下"可选修饰词"，且共享 ≥ 2 个核心 token 时，仍判定为 high：

`YIELD` · `INDEX` · `RATE` · `PRICE` · `FUTURES` · `CLOSE` · `SETTLE`

例：`CGB_3Y` vs `CGB_YTM_3Y` → canonicalize 后为 `CGB_3Y` vs `CGB_YIELD_3Y`，差 `YIELD`（可选修饰词），共享 `CGB` + `3Y` ≥ 2 → **high**

### confidence（置信度）

最终 confidence 由三个维度综合打分（取平均后映射）：

| 维度 | 来源 | 权重 |
|------|------|------|
| Round 1 confidence | 模型自评 | 1/3 |
| Round 2 confidence | 模型自评 | 1/3 |
| consistency | 比较器判定 | 1/3 |

| 综合分 | 最终 confidence |
|--------|----------------|
| ≥ 2.5 | high |
| ≥ 1.5 | medium |
| < 1.5 | low |

### indicator_id 命名原则

| 原则 | 说明 |
|------|------|
| 语义清晰 | 金融分析师一眼能看出指标含义 |
| 贴近金融研究习惯 | CPI_YOY, PMI_MANU, DR007 等 |
| adjustment 体现在 ID 中 | 同比 → `_YOY`，累计同比 → `_CUM_YOY` |
| 不编码频率转换信息 | "由日度转月度" 是处理方式，不是指标本体 |
| 适合 LLM 理解 | 不是数据库短码，也不是 Wind/Choice 原始代码 |

### 为什么"由日度转月度"不进入 indicator_id？

`indicator_id` 定义的是"这个指标是什么"，而非"这个指标怎么来的"。频率转换（日→月）属于 ETL 处理层面的元数据，应通过 `source_tag` 或单独字段记录，不应污染指标的语义命名。

### 为什么 adjustment 应体现在 indicator_id 中？

同一个指标的不同 adjustment（同比、环比、累计值、水平值）在分析中含义完全不同。`CPI_YOY` 和 `CPI_MOM` 是两个不同的分析对象，必须通过 ID 区分。

## Prompt 完整调用示例

以下展示两个指标的完整 Qwen API 调用过程，包括 system prompt、user message、以及模型的实际返回。

### 示例 1：BRENT_CRUDE（带"由日度转月度"备注）

#### Round 1 调用

**System prompt**（`prompt_round1.txt` 全文）：

```
你是一名金融数据命名设计师，擅长宏观经济、市场分析、量化研究、投资顾问场景下的结构化指标命名。

任务：
针对 1 个中文金融/宏观/市场指标，判断最合适的英文缩写 `indicator_id`，用于：
- 结构化 CSV / JSON
- 大模型输入字段
- 金融分析 / 量化研究 / 投顾系统

命名原则（严格遵守）：
1. 语义清晰，专业简洁，适合大模型理解
2. 使用全大写 + 下划线
3. indicator_id 总 token 数（以下划线分词）控制在 2~5 个，最多不超过 6 个
4. 如果一个金融市场公认缩写已足够清晰，直接采用，不要加后缀
   - XAUUSD ✓（不要写 XAUUSD_FUTURES_CLOSE）
   - DR007 ✓（不要写 DR007_RATE）
   - BRENT_CRUDE ✓（不要写 BRENT_CRUDE_FUTURES_CLOSING_PRICE_USD_BBL）
5. 尽量符合金融研究常见习惯，如：
   - CPI_YOY
   - PMI_MANU
   - EXPORT_AMOUNT_YOY
   - CONSUMER_CONFIDENCE（不加 _INDEX，除非有多个同名指标需要区分）
6. adjustment 若属于指标定义的重要部分，应尽量体现在命名中
   - YoY → _YOY
   - MoM → _MOM
   - Cumulative YoY → _CUM_YOY
   - Annual Target → _ANNUAL（放在尾部）
7. "由日度转月度"这类频率处理信息不进入 indicator_id
8. 不要机械照搬原始代码；但如果原始代码本身已经很规范，可以直接采用
9. 不要写解释型长字段名（如 xxx_FUTURES_CLOSING_PRICE_USD_BBL）
10. 词序应为：主体 + 细分 + 调整方式，例：LOCAL_SPECIAL_BOND_TARGET_ANNUAL

输入字段：
- raw_indicator_code
- current_meaning
- indicator_name
- unit
- adjustment
- source
- data_type
- remark

其中：
- current_meaning / indicator_name 是主要依据
- adjustment 很重要
- remark 仅作辅助背景

你必须只输出合法 JSON，且能被 Python json.loads() 直接解析。
不要输出任何额外文字，不要输出 Markdown，不要输出代码块。

输出格式固定为：
{
  "recommended_indicator_id": "...",
  "alternative_indicator_ids": ["...", "..."],
  "display_name_cn": "...",
  "naming_rationale_short": "...",
  "confidence": "high | medium | low"
}
```

**User message**（由 `runner.py` 根据指标元数据动态拼接）：

```
Raw indicator code: BRENT_CRUDE
Chinese meaning: 期货收盘价(连续):ICE布油
Indicator name: 期货收盘价(连续):ICE布油
Unit: USD/bbl
Adjustment type: Level
Data source: ICE
Data category: Inflation
Note: This indicator is originally 由日度转月度. This is a frequency processing detail — do NOT encode it in the indicator_id.
```

**Qwen 返回**：

```json
{
  "recommended_indicator_id": "BRENT_CRUDE",
  "alternative_indicator_ids": ["BRENT_CRUDE_FUTURES", "ICE_BRENT"],
  "display_name_cn": "ICE布伦特原油期货收盘价",
  "naming_rationale_short": "BRENT_CRUDE 是市场通用缩写，语义清晰且广泛认可，无需添加后缀；adjustment 为 Level，不需额外标注；频率转换细节不纳入命名。",
  "confidence": "high"
}
```

#### Round 2 调用（独立上下文）

**System prompt**（`prompt_round2.txt` 全文）：

```
你是一名金融数据命名审核员，擅长宏观经济、市场分析、量化研究、投资顾问场景下的结构化指标命名审核。

任务：
针对 1 个中文金融/宏观/市场指标，独立判断最合适的英文缩写 `indicator_id`。

注意：
这是一次全新判断。
你不能假设自己知道上一轮答案。
你只能根据当前提供的信息，重新独立给出结果。

命名原则（严格遵守）：
1. 语义清晰，专业简洁，适合结构化字段与大模型理解
2. 使用全大写 + 下划线
3. indicator_id 总 token 数（以下划线分词）控制在 2~5 个，最多不超过 6 个
4. 如果一个金融市场公认缩写已足够清晰，直接采用，不要加后缀
   - XAUUSD ✓（不要写 XAUUSD_FUTURES_CLOSE、XAUUSD_CME_SETTLE）
   - DR007 ✓（不要写 DR007_RATE）
   - BRENT_CRUDE ✓（不要写 BRENT_CRUDE_FUTURES_CLOSING_PRICE_USD_BBL）
5. 尽量符合金融研究常见习惯，如：
   - CPI_YOY
   - PMI_MANU
   - EXPORT_AMOUNT_YOY
   - CONSUMER_CONFIDENCE（不加 _INDEX，除非有多个同名指标需要区分）
6. adjustment 若属于指标定义的重要部分，应尽量体现在命名中
   - YoY → _YOY
   - MoM → _MOM
   - Cumulative YoY → _CUM_YOY
   - Annual Target → _ANNUAL（放在尾部）
7. "由日度转月度"这类频率处理信息不进入 indicator_id
8. 不要写解释型长字段名（如 xxx_FUTURES_CLOSING_PRICE_USD_BBL）
9. 词序应为：主体 + 细分 + 调整方式，例：LOCAL_SPECIAL_BOND_TARGET_ANNUAL

输入字段：
- raw_indicator_code
- current_meaning
- indicator_name
- unit
- adjustment
- source
- data_type
- remark

你必须只输出合法 JSON，且能被 Python json.loads() 直接解析。
不要输出任何额外文字，不要输出 Markdown，不要输出代码块。

输出格式固定为：
{
  "recommended_indicator_id": "...",
  "alternative_indicator_ids": ["...", "..."],
  "confidence": "high | medium | low"
}
```

**User message**（与 Round 1 完全相同）：

```
Raw indicator code: BRENT_CRUDE
Chinese meaning: 期货收盘价(连续):ICE布油
Indicator name: 期货收盘价(连续):ICE布油
Unit: USD/bbl
Adjustment type: Level
Data source: ICE
Data category: Inflation
Note: This indicator is originally 由日度转月度. This is a frequency processing detail — do NOT encode it in the indicator_id.
```

**Qwen 返回**：

```json
{
  "recommended_indicator_id": "BRENT_CRUDE",
  "alternative_indicator_ids": ["BRENT_CRUDE_FUTURES", "ICE_BRENT"],
  "confidence": "high"
}
```

**比较结果**：R1 = R2 = `BRENT_CRUDE` → consistency = **high**

---

### 示例 2：INFRA_INVEST_CUM_YOY（含 adjustment 的标准宏观指标）

#### Round 1 调用

**User message**：

```
Raw indicator code: INFRA_INVEST_CUM_YOY
Chinese meaning: 基础设施投资:累计同比
Indicator name: 基础设施投资:累计同比
Unit: %
Adjustment type: YoY
Data source: NBS
Data category: Investment
```

**Qwen 返回**：

```json
{
  "recommended_indicator_id": "INFRA_INVEST_CUM_YOY",
  "alternative_indicator_ids": ["INFRASTRUCTURE_INVESTMENT_CUM_YOY", "INFRA_INV_CUM_YOY"],
  "display_name_cn": "基础设施投资累计同比",
  "naming_rationale_short": "采用原始代码 INFRA_INVEST_CUM_YOY，符合金融命名习惯：主体（INFRA_INVEST）+ 调整方式（CUM_YOY），简洁且语义清晰，token数为3，适合结构化数据与模型输入。",
  "confidence": "high"
}
```

#### Round 2 调用（独立上下文）

**User message**（同 Round 1）：

```
Raw indicator code: INFRA_INVEST_CUM_YOY
Chinese meaning: 基础设施投资:累计同比
Indicator name: 基础设施投资:累计同比
Unit: %
Adjustment type: YoY
Data source: NBS
Data category: Investment
```

**Qwen 返回**：

```json
{
  "recommended_indicator_id": "INFRA_INVEST_CUM_YOY",
  "alternative_indicator_ids": ["INFRASTRUCTURE_INVESTMENT_CUM_YOY", "INFRA_INV_CUM_YOY"],
  "confidence": "high"
}
```

**比较结果**：R1 = R2 = `INFRA_INVEST_CUM_YOY` → consistency = **high**

---

### Prompt 设计要点总结

| 要素 | Round 1 | Round 2 |
|------|---------|---------|
| 角色 | 金融数据命名**设计师** | 金融数据命名**审核员** |
| 输出字段 | 5 个（含 display_name_cn、naming_rationale_short） | 3 个（精简，仅 ID + 备选 + confidence） |
| 负面示例 | 3 个（XAUUSD_FUTURES_CLOSE 等） | 4 个（额外加了 XAUUSD_CME_SETTLE） |
| 关键约束 | token 数 2~5、公认缩写直接采用、不编码频率信息 | 同左，另强调"全新判断，不假设上轮答案" |
| temperature | 0.1（低温，提高确定性） | 0.1（同左） |
| User message | 完全相同（保证输入一致性） | 完全相同 |

## 环境配置

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API Key（二选一）
export DASHSCOPE_API_KEY="sk-your-key-here"
# 或在 .env 文件中：
# DASHSCOPE_API_KEY=sk-your-key-here

# 可选：指定模型
export QWEN_MODEL="qwen3-235b-a22b-instruct-2507"
```

## 使用方式

```bash
# 进入 skill 目录
cd skills/reverse_indicator_id

# Dry-run：查看 prompt 但不调用 API
python runner.py --dry-run

# 跑单个指标
python runner.py --only GDP_REAL_YOY

# 全量批量跑
python runner.py

# 自定义输入/输出
python runner.py --input my_indicators.yaml --csv ../../data-type.csv --output-dir my_outputs
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input` | `input_indicators.yaml` | 输入指标 YAML |
| `--csv` | `../../data-type.csv` | CSV 元数据文件 |
| `--supplemental` | `supplemental_metadata.yaml` | 补充元数据 YAML |
| `--output-dir` | `outputs/` | 输出目录 |
| `--only` | 无 | 只处理指定指标 |
| `--dry-run` | false | 不调用 API，仅打印 prompt |

## 输入文件

### input_indicators.yaml

```yaml
indicators:
  - raw_indicator_code: GDP_REAL_YOY
    current_meaning: "中国:GDP:不变价:当季同比"
    remark: ""
```

### data-type.csv

提供 indicator_name, unit, adjustment, source, data_type 等元数据。如果 CSV 中缺失某个指标，自动从 `supplemental_metadata.yaml` 补齐。

## 输出

### reverse_results.json

完整结果，包含两轮原始 response、一致性评估、最终推荐 ID。

### reverse_results.csv

精简表格，适合快速浏览和人工复核。

### 输出示例

```
[1/16] GDP_REAL_YOY — 中国:GDP:不变价:当季同比
  Round 1...
  Round 2...
  -> final_indicator_id=GDP_REAL_YOY  consistency=high  confidence=high

--- Summary ---
  ✓ GDP_REAL_YOY                             -> GDP_REAL_YOY                   [high]
  ✓ BRENT_CRUDE                              -> BRENT_CRUDE                    [high]
  ✓ XAUUSD                                   -> XAUUSD                         [high]
  ✓ M1_YOY                                   -> M1_YOY                         [high]
  ✓ DR007                                    -> DR007                          [high]
  ✓ AA_CREDIT_YIELD_3Y                       -> AA_CREDIT_YIELD_3Y             [high]
  ✓ CGB_3Y                                   -> CGB_3Y                         [high]
  ✓ CONSUMER_CONFIDENCE                      -> CONSUMER_CONFIDENCE            [high]
  ✓ INFRA_INVEST_CUM_YOY                     -> INFRA_INVEST_CUM_YOY           [high]
  ✓ MANUFACTURING_INVEST_CUM_YOY             -> MANU_INVEST_CUM_YOY            [high]
  ✓ REAL_ESTATE_INVEST_CUM_YOY               -> REAL_ESTATE_INVEST_CUM_YOY     [high]
  ✓ PMI_NEW_EXPORT_ORDERS                    -> PMI_NEW_EXPORT_ORDERS          [high]
  ✓ EXPORT_AMOUNT_YOY                        -> EXPORT_AMOUNT_YOY              [high]
  ✓ IMPORT_AMOUNT_YOY                        -> IMPORT_AMOUNT_YOY              [high]
  ✓ SPECIAL_BOND_ISSUE_CUM                   -> SPECIAL_BOND_ISSUE_CUM         [high]
  ✓ LOCAL_SPECIAL_BOND_TARGET_ANNUAL         -> LOCAL_SPECIAL_BOND_TARGET_ANNUAL [high]
```

## 扩展

添加新指标：编辑 `input_indicators.yaml`，添加新条目即可。如果 CSV 中没有对应元数据，在 `supplemental_metadata.yaml` 中补充。
