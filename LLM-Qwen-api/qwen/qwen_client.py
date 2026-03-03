from __future__ import annotations

"""
Qwen API 客户端模块。

结构：
1) 定义错误类型与返回结构
2) 提供 LLMClient 统一发送请求
3) 提供 chat_completions 兼容函数

作用：
封装底层 HTTP 调用细节，让业务层只关注提示词和业务逻辑。
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

try:
    from api_key import load_api_key
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    from api_key import load_api_key

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CHAT_COMPLETIONS_ENDPOINT = "/chat/completions"

Message = Dict[str, str]


class QwenClientError(RuntimeError):
    """客户端通用异常。"""
    pass


class QwenAuthError(QwenClientError):
    """鉴权异常（401/403）。"""
    pass


class QwenRateLimitError(QwenClientError):
    """限流异常（429）。"""
    pass


class QwenServerError(QwenClientError):
    """服务端异常（5xx）。"""
    pass


class QwenResponseError(QwenClientError):
    """响应结构或格式异常。"""
    pass


@dataclass(frozen=True)
class ChatResult:
    """统一返回结构：文本内容 + 原始 JSON。"""
    content: str
    raw: Dict[str, Any]


def _build_headers(api_key: str) -> Dict[str, str]:
    """构造请求头。"""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


class LLMClient:
    """可复用的 Qwen 客户端，面向学习和业务场景。"""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: str = "qwen-plus",
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: int = 30,
    ) -> None:
        # 统一初始化：模型、地址、超时和密钥来源都在这里集中配置。
        self.api_key = api_key or load_api_key(
            env_name="DASHSCOPE_API_KEY", fallback_file="api_key.txt"
        )
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        messages: List[Message],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> ChatResult:
        # 请求载荷结构与 OpenAI 兼容模式保持一致。
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # 发送请求并解析核心文本字段。
        response_json = self._request(payload, timeout_seconds=timeout_seconds)
        content = _extract_content(response_json)
        return ChatResult(content=content, raw=response_json)

    def _request(self, payload: Dict[str, Any], *, timeout_seconds: Optional[int]) -> Dict[str, Any]:
        """底层 HTTP 请求：负责超时、网络异常、状态码分层处理。"""
        url = f"{self.base_url}{CHAT_COMPLETIONS_ENDPOINT}"
        headers = _build_headers(self.api_key)
        timeout = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.Timeout as exc:
            raise QwenClientError(f"Request timeout after {timeout}s") from exc
        except requests.RequestException as exc:
            raise QwenClientError(f"Network error: {exc}") from exc

        if resp.status_code in (401, 403):
            raise QwenAuthError(f"Auth error {resp.status_code}: {resp.text}")
        if resp.status_code == 429:
            raise QwenRateLimitError(f"Rate limit (429): {resp.text}")
        if 500 <= resp.status_code <= 599:
            raise QwenServerError(f"Server error {resp.status_code}: {resp.text}")
        if not (200 <= resp.status_code <= 299):
            raise QwenClientError(f"HTTP error {resp.status_code}: {resp.text}")

        try:
            return resp.json()
        except ValueError as exc:
            raise QwenResponseError(f"Response is not valid JSON: {resp.text[:200]}") from exc


def _extract_content(data: Dict[str, Any]) -> str:
    """从返回 JSON 中提取模型输出文本。"""
    try:
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("content is not str")
    except Exception as exc:
        raise QwenResponseError(f"Unexpected response schema: {data}") from exc
    return content


def chat_completions(
    messages: List[Message],
    *,
    model: str = "qwen-plus",
    base_url: str = DEFAULT_BASE_URL,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
    timeout_seconds: int = 30,
) -> ChatResult:
    """函数式兼容入口，便于最小示例或快速调用。"""
    client = LLMClient(model=model, base_url=base_url, timeout_seconds=timeout_seconds)
    return client.chat(messages, temperature=temperature, max_tokens=max_tokens)

