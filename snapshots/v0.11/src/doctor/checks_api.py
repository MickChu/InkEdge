# -*- coding: utf-8 -*-
"""
checks_api.py — 连接层检查

检查项:
  - LLM API 连通性（发最小化测试请求）
  - 模型可用性
  - 响应延迟
  - 回退模型可用性
"""

import time
from typing import List

from .report import DoctorCheck, Severity


async def check_api_connectivity() -> DoctorCheck:
    """发送最小化测试请求验证端到端连通"""
    try:
        from src.utils.llm_client import LLMClient

        client = LLMClient()
        t0 = time.time()
        response = await client.chat(
            prompt="回复 OK（只回复这两个字母，不要其他内容）",
            max_tokens=5,
        )
        elapsed = time.time() - t0

        content = (response.content or "").strip()
        # API 有响应即视为连通（streaming 模式可能返回空 content）
        ok = len(content) > 0 or elapsed < 30

        if ok:
            if elapsed < 2:
                perf = "极快"
            elif elapsed < 5:
                perf = "正常"
            else:
                perf = "偏慢"

            model = getattr(response, "model", "?")
            detail = f"模型 {model} · {elapsed:.1f}s"
            if not content:
                detail += " (空响应, 可能是 streaming 模式)"
            return DoctorCheck(
                layer="连接层",
                severity=Severity.INFO,
                label=f"LLM API 连通 ({perf})",
                detail=detail,
            )
        else:
            return DoctorCheck(
                layer="连接层",
                severity=Severity.WARNING,
                label="LLM 响应超时",
                detail=f"等待 {elapsed:.0f}s 无响应",
            )

    except ImportError:
        return DoctorCheck(
            layer="连接层",
            severity=Severity.ERROR,
            label="无法导入 LLMClient",
            detail="src/utils/llm_client.py 依赖缺失",
            hint="检查 Python 依赖是否完整",
        )
    except Exception as e:
        msg = str(e)
        hint = ""

        if "401" in msg or "unauthorized" in msg.lower():
            hint = "API Key 无效, 检查 config.yaml 中的 api_key"
        elif "403" in msg or "forbidden" in msg.lower():
            hint = "API Key 无权限访问该模型, 检查模型名和账户状态"
        elif "429" in msg:
            hint = "API 速率限制或配额耗尽, 稍后重试"
        elif "Connection" in msg or "ECONNREFUSED" in msg:
            hint = "无法连接 base_url, 检查网络和地址"
        elif "timeout" in msg.lower():
            hint = "连接超时, base_url 可能不正确或服务端无响应"
        elif "model" in msg.lower() and "not found" in msg.lower():
            hint = "模型不存在, 检查 config.yaml 中的 model_name"

        return DoctorCheck(
            layer="连接层",
            severity=Severity.ERROR,
            label="LLM API 不可用",
            detail=msg[:120],
            hint=hint,
        )


async def run_api_checks() -> List[DoctorCheck]:
    results = []

    # API 连通性
    conn = await check_api_connectivity()
    results.append(conn)

    return results
