from __future__ import annotations

"""
批处理脚本：CSV 工单自动分流。

结构：
1) process_csv: 核心批处理逻辑
2) build_parser: 命令行参数定义
3) main: 程序入口

作用：
把单条工单分析能力扩展到真实团队常见的批量处理流程。
"""

import argparse
import csv
from pathlib import Path

from qwen.mini_llm import EcommerceSupportAssistant


def process_csv(input_csv: str, output_csv: str, *, model: str) -> None:
    """读取输入 CSV，逐条调用业务模型并写回结果 CSV。"""
    input_path = Path(input_csv)
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    # 复用同一个业务助手实例，降低重复初始化成本。
    assistant = EcommerceSupportAssistant()
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8-sig", newline="") as fin, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as fout:
        reader = csv.DictReader(fin)
        if "ticket_text" not in (reader.fieldnames or []):
            raise ValueError("Input CSV must contain column: ticket_text")

        fieldnames = list(reader.fieldnames or [])
        fieldnames.extend(["ticket_type", "priority", "reply_draft"])
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for idx, row in enumerate(reader, start=1):
            text = (row.get("ticket_text") or "").strip()
            if not text:
                # 空文本直接走安全默认值，避免脏数据中断流程。
                row["ticket_type"] = "Other"
                row["priority"] = "P2"
                row["reply_draft"] = "您好，已收到您的反馈，我们会尽快为您处理。"
                writer.writerow(row)
                continue

            try:
                # 正常路径：调用业务分析得到三项核心输出。
                result = assistant.analyze_ticket(text, model=model)
                row["ticket_type"] = result.ticket_type
                row["priority"] = result.priority
                row["reply_draft"] = result.reply
            except Exception as exc:
                # 异常路径：保证批处理不中断，回退人工介入。
                row["ticket_type"] = "Other"
                row["priority"] = "P2"
                row["reply_draft"] = f"处理失败，需人工介入: {exc}"
            writer.writerow(row)
            print(f"[{idx}] done")


def build_parser() -> argparse.ArgumentParser:
    """定义命令行参数，便于直接脚本化执行。"""
    parser = argparse.ArgumentParser(description="Batch route e-commerce support tickets from CSV")
    parser.add_argument(
        "--input",
        required=True,
        help="input csv path, must include column: ticket_text",
    )
    parser.add_argument(
        "--output",
        default="output/routed_tickets.csv",
        help="output csv path",
    )
    parser.add_argument(
        "--model",
        default="qwen-plus",
        help="qwen model name",
    )
    return parser


def main() -> None:
    """命令行入口。"""
    parser = build_parser()
    args = parser.parse_args()
    process_csv(args.input, args.output, model=args.model)
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
