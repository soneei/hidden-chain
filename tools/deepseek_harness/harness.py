#!/usr/bin/env python3
"""
DeepSeek Harness — 通用 DeepSeek API 封装层（中立工具模块）
=============================================================
被 Hidden Chain（健康项目）与 知泉 Tomomi（谈判副驾）等共同复用。

设计原则：
- 纯工具：只做 API 调用封装，不含任何业务逻辑 / 提示词 / 方法论。
- Key 安全：API Key 一律从环境变量 DEEPSEEK_API_KEY 读取，绝不硬编码。
- 统一接口：chat() / chat_json() / stream() 覆盖常见调用形态。
- 健壮性：超时、重试、清晰的错误提示。

用法：
    export DEEPSEEK_API_KEY=sk-xxxx            # 或写入 .env（见 load_dotenv）
    from deepseek_harness import DeepSeekHarness

    h = DeepSeekHarness()
    h.chat("你好")                              # 普通对话
    h.chat_json("提取关键信息", schema_hint="返回 JSON 对象")  # 结构化输出
    for chunk in h.stream("写一段话"): ...      # 流式输出

依赖：requests（pip install requests）
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]


# ── 常量 ──────────────────────────────────────────────────────────────────
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 2


def _load_dotenv_simple(path: str | None = None) -> None:
    """从 .env 加载（若存在）。优先用 python-dotenv，否则手动解析 KEY=VALUE。"""
    env_file = Path(path or Path(__file__).resolve().parent.parent.parent / ".env")
    if not env_file.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_file)
        return
    except ImportError:
        pass
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("\"'")
        os.environ.setdefault(key, value)


class DeepSeekError(Exception):
    """DeepSeek 调用异常（含状态码与服务器返回信息）。"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class DeepSeekHarness:
    """DeepSeek 统一调用封装。

    参数：
        api_key:      API Key。默认读环境变量 DEEPSEEK_API_KEY（含 .env）。
        base_url:     服务地址。默认 https://api.deepseek.com
        model:        模型名。默认 deepseek-chat
        timeout:      请求超时（秒）。
        max_retries:  失败自动重试次数。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        _load_dotenv_simple()
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise DeepSeekError(
                "未找到 DeepSeek API Key。请设置环境变量 DEEPSEEK_API_KEY，"
                "或在项目根目录放 .env（DEEPSEEK_API_KEY=sk-xxx）。"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._url = f"{self.base_url}/chat/completions"
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    # ── 底层请求（含重试）──────────────────────────────────────────────
    def _request(
        self,
        payload: dict[str, Any],
        stream: bool = False,
        postprocess: Callable[[dict[str, Any]], Any] | None = None,
    ) -> Any:
        if requests is None:
            raise DeepSeekError("缺少依赖 requests：请先 pip install requests")

        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(
                    self._url,
                    headers=self._headers,
                    json=payload,
                    timeout=self.timeout,
                    stream=stream,
                )
                if resp.status_code == 401:
                    raise DeepSeekError("API Key 无效或已过期（HTTP 401）。", 401)
                if resp.status_code == 429:
                    raise DeepSeekError("请求过于频繁（HTTP 429），请稍后重试。", 429)
                if resp.status_code >= 400:
                    detail = ""
                    try:
                        detail = resp.json().get("error", {}).get("message", "")
                    except Exception:
                        detail = resp.text[:200]
                    raise DeepSeekError(
                        f"DeepSeek API 错误（HTTP {resp.status_code}）：{detail}",
                        resp.status_code,
                    )

                if stream:
                    return resp
                data = resp.json()
                if postprocess:
                    return postprocess(data)
                return data
            except DeepSeekError:
                raise
            except Exception as exc:  # 网络类错误：重试
                last_err = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
        raise DeepSeekError(f"多次尝试后仍失败：{last_err}")

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            return ""

    # ── 公开接口 ────────────────────────────────────────────────────────
    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        messages: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """普通对话。prompt 为必填；system 为可选的系统提示词。"""
        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        return self._request(payload, postprocess=self._extract_text)

    def chat_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = 2000,
        schema_hint: Optional[str] = None,
    ) -> Any:
        """结构化输出：强制模型返回 JSON，并解析为 dict/list。

        schema_hint 可提示期望结构（如「返回 {"summary": str, "score": int}」），
        模型更稳定地给出合法 JSON。
        """
        sys_parts: list[str] = []
        if system:
            sys_parts.append(system)
        sys_parts.append(
            "你必须只输出合法 JSON（不要 markdown 代码块、不要额外文字）。"
        )
        if schema_hint:
            sys_parts.append(f"输出结构要求：{schema_hint}")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "\n".join(sys_parts)},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        text = self._request(payload, postprocess=self._extract_text)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise DeepSeekError(
                f"模型返回的不是合法 JSON，无法解析：{text[:200]}"
            ) from exc

    def stream(self, prompt: str, system: Optional[str] = None) -> Iterator[str]:
        """流式输出：逐段 yield 文本，适合长内容/实时展示。"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "stream": True,
        }
        resp = self._request(payload, stream=True)
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            chunk = line[6:].strip()
            if chunk == "[DONE]":
                break
            try:
                delta = json.loads(chunk)["choices"][0]["delta"].get("content", "")
            except (KeyError, IndexError, TypeError, json.JSONDecodeError):
                delta = ""
            if delta:
                yield delta


if __name__ == "__main__":
    # 冒烟测试：python3 harness.py
    import sys

    try:
        h = DeepSeekHarness()
    except DeepSeekError as e:
        print(f"[✗] {e}")
        sys.exit(1)
    print("[✓] Harness 初始化成功（已读到 DEEPSEEK_API_KEY）")
    print("[→] 尝试一次简单对话……")
    try:
        reply = h.chat("用一句话回答：1+1 等于几？")
        print(f"[✓] 对话成功：{reply.strip()[:80]}")
    except DeepSeekError as e:
        print(f"[✗] 对话失败：{e}")
        sys.exit(1)
