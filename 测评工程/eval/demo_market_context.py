"""
Demo 市场上下文数据

从 市场分析-提示词模板.md 动态分割，单一数据源：
  DEMO_SYSTEM_PROMPT  ← 模板前半（任务目标、角色、约束条件）
  DEMO_DATA_CONTEXT   ← 模板后半（全部宏观/市场/量化数据区块）

模板文件更新后无需改动本模块。
"""

from pathlib import Path

_TEMPLATE_PATH = Path(__file__).parent / "市场分析-提示词模板.md"
_template_text = _TEMPLATE_PATH.read_text(encoding="utf-8")

# 以 "# 宏观经济数据" 一级标题为界拆分提示词与数据
_SPLIT_MARKER = "\n# 宏观经济数据\n"
_prompt_part, _data_part = _template_text.split(_SPLIT_MARKER, 1)

DEMO_SYSTEM_PROMPT: str = _prompt_part.strip()
DEMO_DATA_CONTEXT: str = "# 宏观经济数据\n" + _data_part
