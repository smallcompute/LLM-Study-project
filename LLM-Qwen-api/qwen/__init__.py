"""
qwen 包导出入口。

结构：
集中导出常用类型与能力，外部只需从 qwen 包导入。

作用：
简化调用路径，避免业务层依赖内部文件结构。
"""

from qwen.mini_llm import EcommerceSupportAssistant, TicketResult, classify_news
from qwen.qwen_client import ChatResult, LLMClient, chat_completions

__all__ = [
    "ChatResult",
    "LLMClient",
    "EcommerceSupportAssistant",
    "TicketResult",
    "chat_completions",
    "classify_news",
]

