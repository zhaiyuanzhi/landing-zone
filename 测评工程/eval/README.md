# 市场分析智能体 · 自动化评测 & 提示词迭代系统

基于 **Claude claude-opus-4-6** 作为评测器，自动评估 **qwen3-235b-a22b-instruct-2507** 市场分析智能体的回复质量，并基于评分结果循环迭代优化系统提示词。

---

## 目录

- [系统概览](#系统概览)
- [快速开始](#快速开始)
- [文件结构](#文件结构)
- [核心流程](#核心流程)
- [评分维度](#评分维度)
- [配置参数](#配置参数)
- [常用命令](#常用命令)
- [输出文件说明](#输出文件说明)
- [常见问题](#常见问题)

---

## 系统概览

```
┌─────────────────────────────────────────────────────────────┐
│                    eval_pipeline.py（主编排）                  │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ agent_runner │ →  │  evaluator   │ →  │   optimizer  │  │
│  │  (qwen3调用)  │    │ (Claude评测) │    │ (Claude优化) │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         ↑                   ↓                    ↓          │
│   系统提示词           7维度评分              改进后提示词      │
│  (market_context)     + 缺陷分析           → 下一轮迭代       │
└─────────────────────────────────────────────────────────────┘
```

**工作原理：**

1. 用当前系统提示词 + 市场上下文数据调用 qwen3，获取市场分析回复
2. Claude claude-opus-4-6（开启自适应思考）对回复进行 7 维度评分
3. 若加权均分 ≥ 阈值（默认 7.5/10）则停止，否则 Claude 针对薄弱维度优化提示词
4. 用新提示词重复上述步骤，最多迭代 5 轮
5. 输出最优提示词，可一键回写至 `market_context.py`

---

## 快速开始

### 1. 安装依赖

```bash
cd eval
pip install -r requirements.txt
```

### 2. 配置 API 密钥

```bash
# Anthropic（评测器 & 优化器）
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

# Qwen3（市场分析智能体）
export QWEN_API_KEY=sk-xxxxxxxxxxxxxxxx

# API 接入点（按实际服务商填写）
export QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

> **常见服务商 BASE_URL：**
> - 阿里云 DashScope：`https://dashscope.aliyuncs.com/compatible-mode/v1`
> - 硅基流动：`https://api.siliconflow.cn/v1`
> - 本地 vLLM：`http://localhost:8000/v1`

### 3. 运行

```bash
# 完整流程（评测 + 自动迭代优化）
python eval_pipeline.py

# 仅评测当前提示词，不优化
python eval_pipeline.py --eval-only
```

---

## 文件结构

```
eval/
├── eval_pipeline.py      # 主编排入口，CLI 命令从这里运行
├── eval_config.py        # 所有配置：API密钥、阈值、测试查询集、权重
├── eval_rubric.py        # 7 维度评分标准定义 + 工具函数
├── agent_runner.py       # 调用 qwen3（OpenAI 兼容接口）
├── evaluator.py          # Claude 评测器（Pydantic 结构化输出）
├── prompt_optimizer.py   # Claude 提示词优化器（XML 标签输出）
├── report.py             # 结果查看器（汇总/详情/Diff/趋势）
├── apply_prompt.py       # 将最优提示词回写 market_context.py
├── requirements.txt      # Python 依赖
└── eval_results/         # 运行后自动生成
    ├── iteration_1.json  # 第 1 轮完整评测数据
    ├── iteration_2.json
    ├── optimization_1.json  # 第 1 轮优化记录（改动摘要 + 预期提升）
    ├── prompt_v2.md      # 第 2 轮使用的提示词（第 1 轮优化结果）
    ├── prompt_v3.md
    ├── best_prompt.md    # 历史最高分对应的提示词
    └── summary.json      # 总体结果摘要
```

> **与主项目的关系：**
> - `agent_runner.py` 和 `eval_pipeline.py` 会向上一级导入 `market_context.py`（通过 `sys.path` 动态添加）
> - `apply_prompt.py` 会修改上一级的 `market_context.py`，操作前自动备份为 `.py.bak`

---

## 核心流程

### 完整迭代循环

```
初始提示词（market_context.SYSTEM_PROMPT）
        │
        ▼
┌───────────────────────────────┐
│  对每条测试查询调用 qwen3 智能体  │  ← 3 条覆盖不同分析诉求的查询
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│  Claude 对每条回复进行 7 维度评分 │  ← adaptive thinking 保证评分深度
│  + 分析"提示词设计缺陷"          │
└───────────────────────────────┘
        │
        ▼
   加权均分 ≥ 7.5 ？
     ┌───┤
    Yes  No
     │    │
   停止   ▼
        ┌───────────────────────────────┐
        │  Claude 针对薄弱维度优化提示词   │  ← 保留优势、精准修复
        └───────────────────────────────┘
              │
              ▼
           下一轮（最多 5 轮）
```

### 断点续跑

如果某轮因网络或配额问题中断，可从任意已保存的提示词版本恢复：

```bash
python eval_pipeline.py --resume-from eval_results/prompt_v3.md
```

---

## 评分维度

Claude 从以下 7 个维度评分（1–10 分，可用 0.5 步长），按权重加权求和：

| # | 维度 | 权重 | 评分要点 |
|---|------|------|---------|
| 1 | **结构完整性** | 20% | 是否包含系统提示词要求的全部 7 个分析模块（核心结论/宏观/结构/资金/技术/催化剂/操作建议） |
| 2 | **数据引用准确性** | 20% | 引用的数字与提供的市场数据完全一致，无捏造、无错误 |
| 3 | **分析深度** | 20% | 超越数据复述，提供因果推断和前瞻性判断，宏观-中观-微观贯通 |
| 4 | **结论明确性** | 15% | ≤3 句话内给出：多/空/震荡方向 + 置信度（高/中/低）+ 核心依据 |
| 5 | **操作可行性** | 10% | 五要素齐备：方向 / 仓位比例 / 时间窗口 / 重点板块 / 规避板块 |
| 6 | **专业性** | 10% | 事实与判断明确区分，适合机构投资者晨会/研报场景 |
| 7 | **风险提示** | 5% | 每个风险事件均附有具体名称 + 明确日期 |

每个维度的评分理由均会引用回复中的具体内容，确保评分可追溯。

---

## 配置参数

所有可调参数集中在 `eval_config.py`：

```python
# 目标分数：达到后停止迭代
SCORE_THRESHOLD = 7.5

# 最大迭代轮次
MAX_ITERATIONS = 5

# 各维度权重（总和须为 1.0）
DIMENSION_WEIGHTS = {
    "structure_completeness": 0.20,
    "data_accuracy":          0.20,
    "analysis_depth":         0.20,
    "conclusion_clarity":     0.15,
    "actionability":          0.10,
    "professionalism":        0.10,
    "risk_disclosure":        0.05,
}

# 测试查询集（可增减）
TEST_QUERIES = [
    "请对今日A股市场进行综合解读...",
    "当前宏观环境下，北向资金持续流出...",
    "基于今日全球市场联动数据，给出明日A股操作建议...",
]

# 模型配置
EVALUATOR_MODEL = "claude-opus-4-6"   # 评测器
OPTIMIZER_MODEL = "claude-opus-4-6"   # 优化器
QWEN_MODEL      = "qwen3-235b-a22b-instruct-2507"
```

---

## 常用命令

### eval_pipeline.py — 主流程

```bash
# 完整流程（默认：最多 5 轮迭代，目标 7.5 分）
python eval_pipeline.py

# 仅评测，不优化提示词
python eval_pipeline.py --eval-only

# 指定最大迭代次数
python eval_pipeline.py --iterations 3

# 从第 3 版提示词断点续跑
python eval_pipeline.py --resume-from eval_results/prompt_v3.md

# 组合使用
python eval_pipeline.py --resume-from eval_results/prompt_v2.md --iterations 2
```

### report.py — 结果查看

```bash
# 汇总 + 各轮得分趋势（默认）
python report.py

# 查看第 2 轮的详细评分和反馈
python report.py --iteration 2
python report.py -i 2

# 对比第 1 轮和第 3 轮提示词的 Diff
python report.py --diff 1 3
python report.py -d 1 3

# 只显示得分趋势表
python report.py --scores
python report.py -s
```

### apply_prompt.py — 回写提示词

```bash
# 预览变更（不实际写入）
python apply_prompt.py --dry-run

# 应用最优提示词到 market_context.py
python apply_prompt.py

# 应用指定版本的提示词
python apply_prompt.py --from eval_results/prompt_v3.md

# 列出所有可用的已保存提示词
python apply_prompt.py --list
```

---

## 输出文件说明

### `eval_results/summary.json`

```json
{
  "completed_at": "2026-03-31T10:30:00",
  "total_iterations": 3,
  "best_score": 8.12,
  "score_threshold": 7.5,
  "achieved_goal": true,
  "score_history": [
    {"iteration": 1, "score": 6.85},
    {"iteration": 2, "score": 7.43},
    {"iteration": 3, "score": 8.12}
  ]
}
```

### `eval_results/iteration_N.json`

每轮的完整评测数据，包含：
- 本轮使用的系统提示词全文
- 每条测试查询的 7 维度评分、得分理由、改进建议
- 提示词缺陷分析（用于驱动下一轮优化）
- 加权总分

### `eval_results/optimization_N.json`

第 N 轮的优化记录：
- `changes_summary`：本次改动了哪些内容及原因
- `expected_improvements`：预期在哪些维度提升多少分

---

## 常见问题

**Q: Qwen3 API 调用失败？**

检查以下几点：
1. `QWEN_API_KEY` 和 `QWEN_BASE_URL` 环境变量是否正确设置
2. `QWEN_BASE_URL` 末尾不要加 `/`（`/v1` 结尾即可）
3. 模型名称是否与服务商支持的一致（可在 `eval_config.py` 的 `QWEN_MODEL` 修改）

**Q: Claude 评测报错 `output_config` 不支持？**

升级 Anthropic SDK：`pip install --upgrade anthropic`（需 ≥ 0.50.0）

**Q: 想提高评测精度？**

在 `eval_config.py` 中增加 `TEST_QUERIES` 数量（建议 5–10 条），覆盖更多市场情景（如单边行情、震荡市、重大事件日等）。

**Q: 想调整迭代方向（如更注重分析深度）？**

修改 `eval_config.py` 中的 `DIMENSION_WEIGHTS`，提高 `analysis_depth` 的权重即可。注意权重总和须保持 1.0。

**Q: apply_prompt.py 误操作怎么恢复？**

脚本在写入前会自动备份：`market_context.py.bak`，直接覆盖即可：

```bash
copy market_context.py.bak market_context.py   # Windows
cp market_context.py.bak market_context.py     # Linux/macOS
```
