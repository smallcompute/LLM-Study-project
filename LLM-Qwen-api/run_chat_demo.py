from qwen.qwen_client import LLMClient


def main() -> None:
    # 结构：初始化客户端 -> 构造消息 -> 打印模型回复。
    # 作用：演示最小可用的 Qwen 聊天调用链路。
    client = LLMClient()
    result = client.chat(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Use one sentence to explain SFT."},
        ],
        temperature=0.2,
    )
    print(result.content)


if __name__ == "__main__":
    main()

