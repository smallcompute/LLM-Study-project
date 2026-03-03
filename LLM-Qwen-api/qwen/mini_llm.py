from __future__ import annotations

"""
电商售后业务模块。

结构：
1) 通用标签清洗与兼容示例函数 classify_news
2) 售后工单结果结构 TicketResult
3) 业务主类 EcommerceSupportAssistant
   - analyze_ticket: 工单类型 + 优先级 + 回复草稿
   - _repair_label: 标签纠错兜底
   - _draft_reply: 客服回复生成

作用：
把通用 LLM 调用能力封装成可直接落地的业务能力。
"""

from dataclasses import dataclass
from typing import List

from qwen.qwen_client import LLMClient, chat_completions


def _normalize_label(text: str) -> str:
    """标准化模型输出，避免换行/引号导致的标签不匹配。"""
    cleaned = text.strip().strip("`").strip("\"'").splitlines()[0].strip()
    return cleaned


def classify_news(text: str, categories: List[str], *, model: str = "qwen-plus") -> str:
    """
    兼容保留函数：最小文本分类示例。

    作用：
    作为基础教学函数，展示“候选约束 + 一次重试纠错”的经典模式。
    """
    if not text.strip():
        raise ValueError("text must not be empty")
    if not categories:
        raise ValueError("categories must not be empty")

    category_str = ", ".join(categories)

    messages = [
        {
            "role": "system",
            "content": "You are a text classifier. Output only one label.",
        },
        {
            "role": "user",
            "content": (
                f"Candidate labels: [{category_str}]\n"
                f"Text: {text}\n"
                "Return exactly one label from candidate labels."
            ),
        },
    ]
    # 第一轮分类：要求模型仅输出候选标签之一。
    result = chat_completions(messages, model=model, temperature=0, timeout_seconds=30)
    label = _normalize_label(result.content)
    if label in categories:
        return label

    retry_messages = [
        {
            "role": "system",
            "content": "Output must be exactly one candidate label, nothing else.",
        },
        {
            "role": "user",
            "content": (
                f"Candidate labels: [{category_str}]\n"
                f"Previous output: {label}\n"
                "Try again and output exactly one valid label."
            ),
        },
    ]
    # 第二轮纠错：当第一轮输出不在候选集合中时触发。
    retry_result = chat_completions(
        retry_messages, model=model, temperature=0, timeout_seconds=30
    )
    retry_label = _normalize_label(retry_result.content)
    if retry_label in categories:
        return retry_label

    raise RuntimeError(
        f"Model output not in candidates. first={label!r}, retry={retry_label!r}"
    )


@dataclass(frozen=True)
class TicketResult:
    """工单分析输出结构。"""
    ticket_type: str
    priority: str
    reply: str


class EcommerceSupportAssistant:
    """
    场景主类：电商售后工单智能分流。

    作用：
    把一条售后文本转为可执行的客服动作信息。
    """

    CATEGORIES = ["Refund", "Logistics", "ProductQuality", "UsageHelp", "Other"]
    PRIORITIES = ["P0", "P1", "P2"]

    def __init__(self, *, client: LLMClient | None = None) -> None:
        # 允许外部注入 client，便于后续测试或替换模型配置。
        self.client = client or LLMClient()

    def analyze_ticket(self, text: str, *, model: str = "qwen-plus") -> TicketResult:
        """
        核心业务流程：
        1) 分类工单类型
        2) 评估处理优先级
        3) 生成客服回复草稿
        """
        if not text.strip():
            raise ValueError("text must not be empty")
        category_str = ", ".join(self.CATEGORIES)
        priority_str = ", ".join(self.PRIORITIES)

        label_messages = [
            {
                "role": "system",
                "content": (
                    "You are an e-commerce support ticket classifier. "
                    "Return exactly one ticket type from candidate labels."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Candidate labels: [{category_str}]\n"
                    f"User ticket: {text}\n"
                    "Output one label only."
                ),
            },
        ]
        # 阶段一：判定工单类型（退款/物流/质量/使用帮助/其他）。
        label_result = self.client.chat(label_messages, model=model, temperature=0)
        label = _normalize_label(label_result.content)
        if label not in self.CATEGORIES:
            label = self._repair_label(label, category_str, model)

        priority_messages = [
            {
                "role": "system",
                "content": (
                    "You are a support ticket triage assistant. "
                    "Return exactly one priority from candidate priorities."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Candidate priorities: [{priority_str}]\n"
                    f"Ticket type: {label}\n"
                    f"User ticket: {text}\n"
                    "Rule: P0=legal risk/brand crisis, P1=urgent loss, P2=normal issue.\n"
                    "Output one priority only."
                ),
            },
        ]
        # 阶段二：判定优先级（P0/P1/P2），异常情况默认降级为 P2。
        priority_result = self.client.chat(priority_messages, model=model, temperature=0)
        priority = _normalize_label(priority_result.content)
        if priority not in self.PRIORITIES:
            priority = "P2"

        # 阶段三：结合类型和优先级生成客服可用回复草稿。
        reply = self._draft_reply(text=text, ticket_type=label, priority=priority, model=model)
        return TicketResult(ticket_type=label, priority=priority, reply=reply)

    def _repair_label(self, bad_label: str, category_str: str, model: str) -> str:
        """标签纠错子流程：强约束重试一次，失败回退为 Other。"""
        retry_messages = [
            {"role": "system", "content": "Output exactly one candidate label."},
            {
                "role": "user",
                "content": (
                    f"Candidate labels: [{category_str}]\n"
                    f"Previous output: {bad_label}\n"
                    "Try again."
                ),
            },
        ]
        retry = self.client.chat(retry_messages, model=model, temperature=0)
        fixed = _normalize_label(retry.content)
        return fixed if fixed in self.CATEGORIES else "Other"

    def _draft_reply(self, text: str, ticket_type: str, priority: str, model: str) -> str:
        """回复草稿子流程：输出简短、礼貌、可直接人工复核的回复。"""
        reply_messages = [
            {
                "role": "system",
                "content": "You are a customer support expert. Write a concise and polite reply.",
            },
            {
                "role": "user",
                "content": (
                    f"Ticket type: {ticket_type}\n"
                    f"Priority: {priority}\n"
                    f"User ticket: {text}\n"
                    "Write a customer-facing reply in Chinese, within 80 words."
                ),
            },
        ]
        result = self.client.chat(reply_messages, model=model, temperature=0.4)
        return result.content.strip()

