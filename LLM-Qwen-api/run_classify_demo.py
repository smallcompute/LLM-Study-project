from qwen.mini_llm import EcommerceSupportAssistant


def main() -> None:
    # 结构：准备工单文本 -> 调用业务助手 -> 输出三项结果。
    # 作用：演示电商售后场景的一条工单完整分析流程。
    ticket = "收到的耳机左耳没有声音，已经影响正常使用，希望尽快处理。"
    assistant = EcommerceSupportAssistant()
    result = assistant.analyze_ticket(ticket, model="qwen-plus")
    print("Ticket Type:", result.ticket_type)
    print("Priority:", result.priority)
    print("Reply Draft:", result.reply)


if __name__ == "__main__":
    main()

