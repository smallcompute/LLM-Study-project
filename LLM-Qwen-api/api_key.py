"""
API Key 管理模块。

结构：
1) 优先读取环境变量（生产推荐）
2) 其次读取本地文件（开发兜底）

作用：
为项目提供统一、可复用的密钥加载入口。
"""

from __future__ import annotations

import os
from pathlib import Path


class ApiKeyError(RuntimeError):
    """无法解析 API Key 时抛出。"""


def load_api_key(
    env_name: str = "API_KEY",
    fallback_file: str | None = "api_key.txt",
    required: bool = True,
) -> str:
    """
    结构：
    1) 读取环境变量
    2) 读取本地兜底文件
    3) 必需模式下抛出明确异常

    作用：
    给所有调用方提供统一且安全的 API Key 获取逻辑。
    """
    # 第一步：环境变量优先，适合生产环境与 CI。
    key = os.getenv(env_name, "").strip()
    if key:
        return key

    # 第二步：本地文件兜底，便于本地开发调试。
    if fallback_file:
        path = Path(fallback_file)
        if path.exists():
            file_key = path.read_text(encoding="utf-8").strip()
            if file_key:
                return file_key

    # 第三步：缺失时快速失败，避免配置问题被静默忽略。
    if required:
        raise ApiKeyError(
            f"Missing API key. Set env var '{env_name}'"
            + (f" or provide '{fallback_file}'." if fallback_file else ".")
        )
    return ""


if __name__ == "__main__":
    # 本地自检入口：验证密钥读取链路，并掩码展示避免泄漏。
    try:
        demo_key = load_api_key(env_name="DASHSCOPE_API_KEY", fallback_file="api_key.txt")
        masked = demo_key[:4] + "***" + demo_key[-4:] if len(demo_key) >= 8 else "***"
        print(f"API key loaded: {masked}")
    except ApiKeyError as exc:
        print(exc)

