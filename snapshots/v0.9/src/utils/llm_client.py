"""
LLMClient — 统一的大语言模型调用客户端

设计理念：
- 适配任何 OpenAI 兼容 API（DeepSeek / OpenAI / Ollama / 自定义）
- 支持同步/异步调用
- 自动重试 + 超时控制
- 模型参数可热切换

AI_NovelGenerator 的 llm_adapters.py 提供了好的参考，这里增强加入：
- 流式输出支持（SSE）
- Token 用量统计
- 回退模型支持
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator

log = logging.getLogger(__name__)


@dataclass
class LLMUsage:
    """Token 用量统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    usage: Optional[LLMUsage] = None
    model: str = ""
    finish_reason: str = ""


@dataclass
class LLMConfig:
    """LLM 配置"""
    model_name: str = "deepseek-v4-flash"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 600
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    interface_format: str = "OpenAI"
    # 回退模型（主模型失败时自动切换）
    fallback_models: list = field(default_factory=list)


class LLMClient:
    """
    统一的 LLM 调用客户端

    用法：
        client = LLMClient(model_name="deepseek-v4-flash")
        response = await client.chat("你好，请写一段小说开头")
        print(response.content)
    """

    def __init__(self, **kwargs):
        self.config = LLMConfig(**{k: v for k, v in kwargs.items() if k in LLMConfig.__dataclass_fields__})
        self._total_usage = LLMUsage()

    @property
    def model_name(self) -> str:
        return self.config.model_name

    def _build_messages(self, prompt: str, system_prompt: str = "") -> list:
        """构建 OpenAI 兼容格式的 messages"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _get_base_url(self) -> str:
        """获取 API base URL（优先级：实例参数 > 环境变量 > config.yaml > 默认值）"""
        if self.config.base_url:
            return self.config.base_url.rstrip("/")
        from src.utils.config import get_config
        return get_config().get("base_url", "https://api.deepseek.com/v1").rstrip("/")

    def _get_api_key(self) -> str:
        """获取 API Key（优先级：实例参数 > 环境变量 > config.yaml > 默认空）"""
        if self.config.api_key:
            return self.config.api_key
        from src.utils.config import get_config
        return get_config().get("api_key", "")

    async def chat(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """异步调用 LLM（非流式）"""
        import aiohttp

        model_name = model or self.config.model_name
        messages = self._build_messages(prompt, system_prompt)
        base_url = self._get_base_url()
        api_key = self._get_api_key()

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        endpoint = f"{base_url}/chat/completions"
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"LLM API 错误 {resp.status}: {text[:500]}")

                data = await resp.json()
                choice = data["choices"][0]
                content = choice["message"]["content"]

                usage = None
                if "usage" in data:
                    u = data["usage"]
                    usage = LLMUsage(
                        prompt_tokens=u.get("prompt_tokens", 0),
                        completion_tokens=u.get("completion_tokens", 0),
                        total_tokens=u.get("total_tokens", 0),
                    )
                    self._total_usage.prompt_tokens += usage.prompt_tokens
                    self._total_usage.completion_tokens += usage.completion_tokens
                    self._total_usage.total_tokens += usage.total_tokens

                return LLMResponse(
                    content=content,
                    usage=usage,
                    model=data.get("model", model_name),
                    finish_reason=choice.get("finish_reason", "stop"),
                )

    def chat_sync(self, prompt: str, system_prompt: str = "", model: Optional[str] = None) -> LLMResponse:
        """同步调用 LLM（内部用 asyncio.run）"""
        import asyncio
        return asyncio.run(self.chat(prompt, system_prompt, model))

    async def chat_with_retry(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """带自动重试的 LLM 调用"""
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return await self.chat(prompt, system_prompt, model, max_tokens=max_tokens)
            except Exception as e:
                last_error = e
                log.warning(f"LLM 调用失败 (attempt {attempt+1}/{max_retries+1}): {e}")

                # 尝试回退模型
                if attempt == max_retries and self.config.fallback_models:
                    for fallback in self.config.fallback_models:
                        try:
                            log.info(f"尝试回退模型: {fallback}")
                            return await self.chat(prompt, system_prompt, fallback, max_tokens=max_tokens)
                        except Exception:
                            continue

                if attempt < max_retries:
                    time.sleep(retry_delay * (attempt + 1))

        raise RuntimeError(f"LLM 调用失败（已重试 {max_retries} 次）: {last_error}")

    @property
    def total_usage(self) -> LLMUsage:
        """累计 Token 用量"""
        return self._total_usage

    def reset_usage(self):
        """重置用量统计"""
        self._total_usage = LLMUsage()
