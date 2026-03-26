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
