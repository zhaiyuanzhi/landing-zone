# 市场分析智能体 · 自动化评测 & 提示词迭代系统

基于多模型集成评测器，自动评估市场分析智能体的回复质量，并基于评分结果循环迭代优化系统提示词。

---

## 目录

- [系统概览](#系统概览)
- [快速开始](#快速开始)
- [可视化 Dashboard](#可视化-dashboard)
- [文件结构](#文件结构)
- [核心流程](#核心流程)
- [数据来源](#数据来源)
- [评分维度](#评分维度)
- [多模型集成评测器](#多模型集成评测器)
- [提示词优化器](#提示词优化器)
- [配置参数](#配置参数)
- [常用命令](#常用命令)
- [输出文件说明](#输出文件说明)
- [常见问题](#常见问题)

---

## 系统概览

```
┌──────────────────────────────────────────────────────────────────┐
│                    eval_pipeline.py（主编排）                       │
│                                                                  │
│  ┌──────────────┐    ┌───────────────────┐    ┌──────────────┐  │
│  │ agent_runner │ →  │ evaluator_ensemble│ →  │   optimizer  │  │
│  │ (qwen3 调用)  │    │ (多模型集成评测)    │    │ (多模型可选) │  │
│  └──────────────┘    └───────────────────┘    └──────────────┘  │
│         ↑                     ↓                       ↓          │
│   系统提示词 +            7 维度集成评分             改进后提示词    │
│   市场数据上下文           + 缺陷分析              → 下一轮迭代     │
└──────────────────────────────────────────────────────────────────┘
```

**工作原理：**

1. 用当前系统提示词 + 市场上下文数据调用 qwen3，获取市场分析回复
2. 多个评测器（豆包/DeepSeek-R1/Claude 等）对回复进行 7 维度评分，取加权平均
3. 若加权均分 ≥ 阈值（默认 7.5/10）则停止，否则优化器针对薄弱维度改写提示词
4. 用新提示词重复上述步骤，最多迭代 N 轮
5. 回答文件自动落盘至 `eval_results/responses/`，方便人工核查

---

## 快速开始

### 1. 安装依赖

```bash
cd eval
pip install -r requirements.txt
```

### 2. 配置 API 密钥

```bash
# 智能体（被评测方）
export QWEN_API_KEY=your_qwen_api_key

# 评测器（至少配置一个）
export DOUBAO_API_KEY=xxx
export DEEPSEEK_API_KEY=xxx
export ANTHROPIC_API_KEY=your_anthropic_api_key

export QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export QWEN_API_KEY=xxx
export QWEN_EVAL_API_KEY=xxx

# 优化器（与评测器共用，按 OPTIMIZER_CONFIG 中的 api_key_env 读取）
# 若优化器选 DeepSeek-R1，则使用 DEEPSEEK_API_KEY，无需额外配置
```

> **常见 BASE_URL：**
> - 阿里云 DashScope：`https://dashscope.aliyuncs.com/compatible-mode/v1`
> - 火山引擎（豆包）：`https://ark.cn-beijing.volces.com/api/v3`
> - DeepSeek：`https://api.deepseek.com/v1`
> - 硅基流动：`https://api.siliconflow.cn/v1`

### 3. 运行

```bash
# 完整流程（评测 + 自动迭代优化）
python eval_pipeline.py

# 仅评测当前提示词，不优化
python eval_pipeline.py --eval-only

# 已有回答文件时直接跳到评测阶段（默认行为，节省 LLM 调用费用）
python eval_pipeline.py --eval-only

# 强制重新生成回答（忽略已有缓存文件）
python eval_pipeline.py --eval-only --force-regen
```

---

## 可视化 Dashboard

基于 FastAPI + Chart.js 的 Web 可视化界面，一键查看所有评测数据，无需阅读 JSON 文件。

### 启动

```bash
cd eval
uvicorn dashboard:app --reload --port 8765
# 访问 http://localhost:8765
```

### 功能模块

| 模块 | 内容 |
|------|------|
| **顶部状态栏** | 达标状态（已达标 / 进行中）、迭代轮次、阈值 |
| **统计概览** | 最高综合得分、迭代轮次、启用评测器数、测试查询数、目标状态 |
| **模型配置** | 被测智能体（Qwen3）、各评测器启用/禁用状态及参数、提示词优化器 |
| **测评集** | 全部测试查询列表 |
| **分数趋势图** | 折线图展示各轮综合得分变化，标记达标阈值线；雷达图展示最新迭代各维度得分 |
| **维度对比表** | 每个评分维度的权重、各轮得分条形图、轮次间变化量 Δ、评测器一致性（标准差） |
| **提示词查看器** | 左侧版本列表（含各版本得分），右侧展示完整提示词内容，点击切换 |

### API 端点

Dashboard 后端提供以下 REST 接口，可直接调用：

```
GET /api/overview              # 模型配置、测试集、维度权重、整体摘要
GET /api/iterations            # 所有迭代的得分和维度分明细
GET /api/iteration/{n}         # 第 n 轮完整评测数据
GET /api/prompts               # 提示词版本列表（v1 / v2 / best…）
GET /api/prompt/{version}      # 指定版本提示词全文（version: v1 / v2 / best）
GET /api/response/{iter}/{q}   # 指定迭代、指定查询的智能体回答原文
```

### 文件

```
eval/
├── dashboard.py          # FastAPI 后端（所有 API 路由）
└── static/
    └── index.html        # 单页前端（Chart.js，无需构建工具）
```

---

## 文件结构

```
eval/
├── 市场分析-提示词模板.md    # 数据唯一来源：提示词 + 全量市场数据
│
├── eval_pipeline.py         # 主编排入口，CLI 命令从这里运行
├── eval_config.py           # 所有配置：模型、API密钥、阈值、查询集、权重
├── eval_rubric.py           # 7 维度评分标准定义 + 工具函数
│
├── demo_market_context.py   # 从模板文件分割 DEMO_SYSTEM_PROMPT / DEMO_DATA_CONTEXT
├── agent_runner.py          # 调用 qwen3（OpenAI 兼容接口），注入数据上下文
│
├── evaluator.py             # 评测器对外接口（向后兼容入口）
├── evaluator_ensemble.py    # 多模型集成协调器
├── evaluator_claude.py      # Claude 评测器（Pydantic 结构化输出）
├── evaluator_oai.py         # 通用 OpenAI 兼容评测器（Doubao/DeepSeek/Qwen）
│
├── prompt_optimizer.py      # 提示词优化器（支持多模型后端）
├── report.py                # 结果查看器（汇总/详情/Diff/趋势）
├── apply_prompt.py          # 将最优提示词写回市场分析提示词模板
├── dashboard.py             # 可视化 Dashboard 后端（FastAPI）
├── requirements.txt         # Python 依赖
│
├── static/
│   └── index.html           # Dashboard 前端（单页，Chart.js）
│
├── data/                    # 历史 CSV 文件（已不参与主流程，仅供参考）
│
└── eval_results/            # 运行后自动生成
    ├── responses/           # 智能体回答文件（人工核查用）
    │   ├── iter1_q1.md      # 第 1 轮 · 第 1 条查询的完整回答
    │   ├── iter1_q2.md
    │   └── ...
    ├── iteration_1.json     # 第 1 轮完整评测数据
    ├── optimization_1.json  # 第 1 轮优化记录（改动摘要 + 预期提升）
    ├── prompt_v2.md         # 第 2 轮使用的提示词（第 1 轮优化结果）
    ├── best_prompt.md       # 历史最高分对应的提示词
    └── summary.json         # 总体结果摘要
```

---

## 核心流程

### 完整迭代循环

```
初始提示词（市场分析-提示词模板.md 前半段）
        │
        ▼
┌─────────────────────────────────┐
│  对每条测试查询调用 qwen3 智能体    │  ← eval_config.TEST_QUERIES
│  （若缓存文件已存在则直接加载）      │
└─────────────────────────────────┘
        │  回答自动保存至 responses/iter{N}_q{M}.md
        ▼
┌─────────────────────────────────┐
│  多评测器并行对每条回复评 7 维度    │  ← doubao / deepseek_r1 / claude 等
│  + 分析「提示词设计缺陷」          │
└─────────────────────────────────┘
        │  集成：各维度取加权平均分
        ▼
   加权均分 ≥ 7.5 ？
     ┌───┤
    Yes  No
     │    │
   停止   ▼
        ┌─────────────────────────────────┐
        │  优化器针对薄弱维度改写提示词       │  ← OPTIMIZER_CONFIG 中配置的模型
        │  保留优势维度，精准修复低分项        │
        └─────────────────────────────────┘
              │  新提示词保存至 prompt_v{N+1}.md
              ▼
           下一轮（最多 MAX_ITERATIONS 轮）
```

### 回答文件缓存机制

```
默认（无 --force-regen）
  └─ responses/iter{N}_q{1..M}.md 全部存在？
        ├─ 是 → 直接加载，跳过 LLM 调用 → 直接进入评测
        └─ 否 → 调用 LLM，生成并保存文件

--force-regen
  └─ 始终重新调用 LLM，覆盖已有文件
```

### 断点续跑

```bash
# 从第 3 版提示词恢复
python eval_pipeline.py --resume-from eval_results/prompt_v3.md
```

---

## 数据来源

所有数据均来自单一文件 **`市场分析-提示词模板.md`**，`demo_market_context.py` 在运行时将其自动分割为两个变量：

| 变量 | 内容 | 作用 |
|------|------|------|
| `DEMO_SYSTEM_PROMPT` | 模板前半：任务目标、角色定义、约束条件 | 注入 system 消息 |
| `DEMO_DATA_CONTEXT` | 模板后半：全部宏观/市场/量化数据区块（CSV 格式） | 注入 user 消息 |

**数据区块（均为月频时间序列）：**

| 区块 | 指标 |
|------|------|
| Growth | GDP_REAL_YOY、INDUSTRY_YOY、RETAIL_SALES_YOY |
| Sentiment | PMI_MANU、PMI_SERV、CONSUMER_CONFIDENCE、PMI_NEW_EXPORT_ORDERS |
| Investment | INFRA/MANU/REAL_ESTATE_INVEST_CUM_YOY |
| Real_Estate | RESID_HOUSE_SALES_CUM_YOY |
| Trade | EXPORT/IMPORT_AMOUNT_CNY_YOY |
| FX | FX_CNY_MID |
| Credit | M2_YOY、M1_YOY、TSF_STOCK_YOY |
| Rate | DR007、CREDIT_YTM_AA_3Y、CGB_3Y_YTM、LPR_1Y |
| Labor | URBAN_SURVEYED_UNEMPLOYMENT_RATE |
| Fiscal | GOV_EXPEND_CUM_YOY、SPECIAL_BOND_PROGRESS/ISSUE_CUM |
| Inflation | BRENT_CRUDE、CPI_YOY、PPI_YOY |
| Risk_Sentiment | VIX、XAUUSD（月均值） |
| 量化风险结构 | 年化波动率、协方差矩阵、相关矩阵、国债利率期限结构 |
| 四大资产画像 | CASH/BOND/EQUITY/ALT 风险收益指标（1Y/3Y/5Y） |

> **更新数据**：直接编辑 `市场分析-提示词模板.md`，代码无需任何改动。

---

## 评分维度

从以下 7 个维度评分（1–10 分，可用 0.5 步长），按权重加权求和：

| # | 维度 | 权重 | 评分要点 |
|---|------|------|---------|
| 1 | **结构完整性** | 20% | 是否包含系统提示词要求的全部分析模块 |
| 2 | **数据引用准确性** | 20% | 引用数字与提供数据完全一致，无捏造 |
| 3 | **分析深度** | 20% | 超越数据复述，提供因果推断和前瞻性判断 |
| 4 | **结论明确性** | 15% | 明确方向 + 置信度 + 核心依据 |
| 5 | **操作可行性** | 10% | 方向 / 时间窗口 / 重点板块等要素齐备 |
| 6 | **专业性** | 10% | 事实与判断明确区分，适合机构投资者场景 |
| 7 | **风险提示** | 5% | 每个风险事件附有具体名称 + 明确日期 |

权重在 `eval_config.DIMENSION_WEIGHTS` 中调整，总和须为 1.0。

---

## 多模型集成评测器

### 架构

```
evaluator.py（对外接口）
    └── evaluator_ensemble.py（集成协调器）
            ├── evaluator_claude.py   Claude claude-opus-4-6（Anthropic 原生）
            └── evaluator_oai.py      通用 OpenAI 兼容层
                    ├── 豆包 Doubao   doubao-seed-2-0-pro-260215
                    ├── DeepSeek-V3   deepseek-chat
                    ├── DeepSeek-R1   deepseek-reasoner（含思维链处理）
                    ├── 千问 Qwen-Max  qwen-max
                    └── 千问 Qwen-Plus qwen-plus
```

### 集成评分机制

```
集成分（每维度） = Σ(评测器i得分 × 评测器i权重) / Σ(权重)
```

额外输出**标准差**衡量评测者分歧：

| 标准差 | 含义 |
|--------|------|
| < 0.8  | 高一致，评测结论可信 |
| 0.8–1.5 | 中等分歧，可参考各评测器原始理由 |
| > 1.5  | 高分歧，建议人工复核该维度 |

### 启用/禁用评测器

在 `eval_config.py` 的 `EVALUATOR_CONFIGS` 中设置 `enabled`：

```python
EVALUATOR_CONFIGS = {
    "claude":      {"enabled": False, ...},  # Anthropic Claude
    "doubao":      {"enabled": True,  "timeout": 180, ...},  # 豆包
    "deepseek_r1": {"enabled": True,  "timeout": 240, ...},  # DeepSeek-R1（推理较慢）
    "deepseek_v3": {"enabled": False, ...},
    "qwen_max":    {"enabled": False, ...},
    "qwen_plus":   {"enabled": False, ...},
}
```

### 各评测器所需环境变量

| 评测器 | 环境变量 |
|--------|---------|
| Claude | `ANTHROPIC_API_KEY` |
| 豆包 Doubao | `DOUBAO_API_KEY` |
| DeepSeek-V3 / R1 | `DEEPSEEK_API_KEY` |
| 千问 Qwen-Max/Plus | `QWEN_EVAL_API_KEY` |

> `QWEN_EVAL_API_KEY` 与智能体侧的 `QWEN_API_KEY` 用途不同，可设同一个值。

### 超时配置

每个评测器配置项均支持 `timeout`（秒），防止 API 调用无限阻塞：

```python
"doubao":      {"timeout": 180, ...},  # 默认 180s
"deepseek_r1": {"timeout": 240, ...},  # R1 推理耗时长，建议 240s+
```

若超时，该评测器本次结果被跳过，其余已完成评测器的结果正常汇总。

### DeepSeek-R1 注意事项

- 响应含思维链（`<think>...</think>` 或 `reasoning_content`），`evaluator_oai.py` 已自动剥离
- **必须设置** `"use_json_mode": False`（R1 不支持 `response_format=json_object`）

### 豆包 Doubao 注意事项

模型名称填写**推理接入点 ID**（格式 `ep-xxxxxxxx-xxxxx`），通过环境变量覆盖默认值：

```bash
export DOUBAO_MODEL=ep-20241228xxxxxx-xxxxx
```

---

## 提示词优化器

优化器同样支持多模型后端，在 `eval_config.py` 的 `OPTIMIZER_CONFIG` 中切换。

### 切换方法

注释掉当前生效的配置，取消注释所需预设：

```python
# ── 当前：DeepSeek-R1（推理模型）────────────────────────────
OPTIMIZER_CONFIG = {
    "provider":        "openai_compat",
    "model":           "deepseek-reasoner",
    "api_key_env":     "DEEPSEEK_API_KEY",
    "base_url":        "https://api.deepseek.com/v1",
    "enable_thinking": False,
    "max_tokens":      8192,
}

# ── 可选：Claude claude-opus-4-6（含 adaptive thinking）──────────────
# OPTIMIZER_CONFIG = {
#     "provider":        "anthropic",
#     "model":           "claude-opus-4-6",
#     "api_key_env":     "ANTHROPIC_API_KEY",
#     "base_url":        None,
#     "enable_thinking": True,
#     "max_tokens":      8192,
# }

# ── 可选：Qwen3-235B（含思维链）──────────────────────────────
# OPTIMIZER_CONFIG = {
#     "provider":        "openai_compat",
#     "model":           "qwen3-235b-a22b-instruct-2507",
#     "api_key_env":     "QWEN_API_KEY",
#     "base_url":        "https://dashscope.aliyuncs.com/compatible-mode/v1",
#     "enable_thinking": True,
#     "max_tokens":      8192,
# }
```

### enable_thinking 说明

| 模型类型 | `enable_thinking: True` 的效果 |
|---------|-------------------------------|
| Anthropic Claude | 开启 `thinking={"type": "adaptive"}` |
| Qwen3 系列 | 附加 `extra_body={"enable_thinking": True}` |
| DeepSeek-R1 | 忽略（R1 内置推理，无需参数） |
| 其他模型 | 忽略 |

---

## 配置参数

所有可调参数集中在 `eval_config.py`：

```python
SCORE_THRESHOLD = 7.5    # 加权均分达到该值则停止迭代
MAX_ITERATIONS  = 1      # 最大迭代轮次

DIMENSION_WEIGHTS = {
    "structure_completeness": 0.20,
    "data_accuracy":          0.20,
    "analysis_depth":         0.20,
    "conclusion_clarity":     0.15,
    "actionability":          0.10,
    "professionalism":        0.10,
    "risk_disclosure":        0.05,
}

TEST_QUERIES = [
    "2026 年整体经济走势如何，对普通投资者有哪些机会？",
    "请帮忙做个市场分析?",
    "目前市场情况如何，理财投资有哪些机会?",
    "黄金现在价位偏高，还适合入场做长期配置吗?",
]
```

---

## 常用命令

### eval_pipeline.py — 主流程

```bash
# 完整流程（评测 + 自动迭代优化）
python3 eval_pipeline.py

# 仅评测，不优化提示词
python3 eval_pipeline.py --eval-only

# 指定最大迭代次数
python3 eval_pipeline.py --iterations 3

# 从第 3 版提示词断点续跑
python3 eval_pipeline.py --resume-from eval_results/prompt_v3.md

# 强制重新调用 LLM（忽略已有回答缓存）
python3 eval_pipeline.py --eval-only --force-regen

# 组合使用
python3 eval_pipeline.py --resume-from eval_results/prompt_v2.md --iterations 2 --force-regen
```

### report.py — 结果查看

```bash
# 汇总 + 各轮得分趋势（默认）
python3 report.py

# 查看第 2 轮的详细评分和反馈
python3 report.py --iteration 2

# 对比第 1 轮和第 3 轮提示词的 Diff
python3 report.py --diff 1 3

# 只显示得分趋势表
python3 report.py --scores

# 查看第 2 轮各评测器维度得分对比矩阵（含标准差）
python3 report.py --evaluators 2
```

**多评测器对比矩阵示例：**

```
====================================================================
  第 2 轮  ·  各评测器维度得分对比
====================================================================
  维度          doubao  deepseek_r1  集成均分  标准差
  ──────────────────────────────────────────────────────────────
  结构完整性       8.0       8.5       8.25    0.25
  数据引用准确     7.5       8.0       7.75    0.25
  分析深度         7.0       7.5       7.25    0.25
  结论明确性       8.0       8.0       8.00    0.00
  操作可行性       7.5       7.5       7.50    0.00
  专业性           8.0       8.5       8.25    0.25
  风险提示         6.5       7.0       6.75    0.25
  ──────────────────────────────────────────────────────────────
  加权总分         7.65      7.90      7.78
====================================================================
```

### apply_prompt.py — 回写提示词

```bash
# 预览变更（不实际写入）
python3 apply_prompt.py --dry-run

# 将最优提示词写回市场分析提示词模板
python3 apply_prompt.py

# 应用指定版本的提示词
python3 apply_prompt.py --from eval_results/prompt_v3.md

# 列出所有可用的已保存提示词
python3 apply_prompt.py --list
```

---

## 输出文件说明

### `eval_results/responses/iter{N}_q{M}.md`

每条查询的完整回答，格式如下：

```markdown
# 第 1 轮 · 查询 1

**查询：** 2026 年整体经济走势如何，对普通投资者有哪些机会？

**Tokens：** 12345

---

[智能体完整回答内容...]
```

- 默认复用已有文件，重新评测无需再次调用 LLM
- `--force-regen` 时覆盖重写

### `eval_results/summary.json`

```json
{
  "completed_at": "2026-03-31T10:30:00",
  "total_iterations": 2,
  "best_score": 7.85,
  "score_threshold": 7.5,
  "achieved_goal": true,
  "score_history": [
    {"iteration": 1, "score": 6.85},
    {"iteration": 2, "score": 7.85}
  ]
}
```

### `eval_results/iteration_N.json`

每轮完整评测数据，包含：
- 本轮使用的系统提示词全文
- 每条测试查询的 7 维度评分、得分理由、改进建议
- 各评测器原始分及标准差（分歧指标）
- 提示词缺陷分析

### `eval_results/optimization_N.json`

第 N 轮的优化记录：
- `changes_summary`：改动了哪些内容及原因
- `expected_improvements`：预期在哪些维度提升多少分

---

## 常见问题

**Q: 已有回答文件，只想重跑评测，不想再调用 LLM？**

直接运行即可，默认行为就是复用缓存：

```bash
python eval_pipeline.py --eval-only
```

**Q: 想强制重新生成所有回答？**

```bash
python eval_pipeline.py --eval-only --force-regen
```

**Q: 评测器 API 调用超时怎么办？**

在 `eval_config.py` 的 `EVALUATOR_CONFIGS` 中增大对应评测器的 `timeout`（单位秒）。DeepSeek-R1 推理较慢，建议设置 240 秒以上。超时后该评测器本次结果跳过，其余已完成评测器正常汇总。

**Q: 如何更新市场数据？**

直接编辑 `市场分析-提示词模板.md` 中的 CSV 数据区块，代码无需任何改动。

**Q: 想切换提示词优化器模型？**

在 `eval_config.py` 中修改 `OPTIMIZER_CONFIG`，内置预设包括 Claude claude-opus-4-6、Qwen3-235B、DeepSeek-R1、豆包，取消注释对应配置块即可。

**Q: 想提高评测精度？**

在 `eval_config.py` 中增加 `TEST_QUERIES` 数量（建议 5–10 条），覆盖更多市场情景；同时启用更多评测器以减少单一模型的偏差。

**Q: 想调整迭代方向（如更注重分析深度）？**

修改 `eval_config.py` 中的 `DIMENSION_WEIGHTS`，提高 `analysis_depth` 的权重即可，总和须保持 1.0。

**Q: Qwen3 API 调用失败？**

1. 检查 `QWEN_API_KEY` 和 `QWEN_BASE_URL` 环境变量是否正确
2. `QWEN_BASE_URL` 末尾不要加 `/`（`/v1` 结尾即可）
3. 检查 `eval_config.py` 中 `QWEN_MODEL` 的模型名称是否与服务商一致
