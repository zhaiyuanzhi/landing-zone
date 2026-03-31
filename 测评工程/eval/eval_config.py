"""
评测流程配置
"""
import os

# ============================================================
# API 配置
# ============================================================

# Anthropic (Claude) —— 用作评测器 & 提示词优化器
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Qwen3 API（OpenAI 兼容接口）
# 阿里云 DashScope 示例: https://dashscope.aliyuncs.com/compatible-mode/v1
# 硅基流动 示例:         https://api.siliconflow.cn/v1
QWEN_API_KEY  = os.environ.get("QWEN_API_KEY", "")
QWEN_BASE_URL = os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL    = os.environ.get("QWEN_MODEL", "qwen3-235b-a22b-instruct-2507")

# 评测 / 优化所用 Claude 模型
EVALUATOR_MODEL   = "claude-opus-4-6"
OPTIMIZER_MODEL   = "claude-opus-4-6"

# ============================================================
# 流程参数
# ============================================================

# 目标分数（0–10），达到后停止迭代
SCORE_THRESHOLD = 7.5

# 最大迭代轮次
MAX_ITERATIONS = 5

# 各评分维度权重（总和须为 1.0）
DIMENSION_WEIGHTS = {
    "structure_completeness": 0.20,   # 结构完整性
    "data_accuracy":          0.20,   # 数据引用准确性
    "analysis_depth":         0.20,   # 分析深度
    "conclusion_clarity":     0.15,   # 结论明确性
    "actionability":          0.10,   # 操作可行性
    "professionalism":        0.10,   # 专业性
    "risk_disclosure":        0.05,   # 风险提示
}

# 测试查询集（覆盖不同分析诉求）
TEST_QUERIES = [
    "请对今日A股市场进行综合解读，重点关注科技板块的轮动信号与北向资金异动",
    "当前宏观环境下，北向资金持续流出与人民币汇率波动意味着什么？如何布局后市？",
    "基于今日全球市场联动数据，给出明日A股操作建议，需标注具体支撑位和阻力位，以及主要风险事件",
]

# 结果输出目录（相对于 eval/ 目录）
RESULTS_DIR = "eval_results"

# ============================================================
# 启动校验
# ============================================================

def validate_config():
    """检查必要的环境变量是否已配置"""
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not QWEN_API_KEY:
        missing.append("QWEN_API_KEY")
    if missing:
        raise EnvironmentError(
            f"缺少必要的环境变量: {', '.join(missing)}\n"
            "请在运行前设置:\n"
            + "\n".join(f"  export {k}=your_key" for k in missing)
        )
