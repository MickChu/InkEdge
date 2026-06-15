# -*- coding: utf-8 -*-
"""
checks_config.py — 配置层检查

检查项:
  - config.yaml 存在 + YAML 格式
  - base_url 非空可解析
  - model_name 非空
  - api_key 格式
"""

from pathlib import Path
from typing import List

from .report import DoctorCheck, Severity


def check_config_exists() -> DoctorCheck:
    cfg = Path("config.yaml")
    if not cfg.exists():
        return DoctorCheck(
            layer="配置层",
            severity=Severity.ERROR,
            label="config.yaml 不存在",
            hint="从模板复制或运行 python main.py doctor --fix",
        )

    try:
        import yaml
        with open(cfg, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            return DoctorCheck(
                layer="配置层",
                severity=Severity.ERROR,
                label="config.yaml 格式错误",
                detail="解析结果不是字典",
                hint="检查 YAML 语法",
            )

        return DoctorCheck(
            layer="配置层",
            severity=Severity.INFO,
            label="config.yaml 存在",
            detail="格式正确",
        )
    except Exception as e:
        return DoctorCheck(
            layer="配置层",
            severity=Severity.ERROR,
            label="config.yaml 解析失败",
            detail=str(e)[:80],
            hint="检查 YAML 语法",
        )


def check_required_fields() -> List[DoctorCheck]:
    results = []
    cfg = Path("config.yaml")
    if not cfg.exists():
        return results

    try:
        import yaml
        with open(cfg, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return results

    required = [
        ("base_url", "LLM API 地址"),
        ("model_name", "模型名称"),
    ]

    for key, desc in required:
        val = data.get(key)
        if not val:
            results.append(DoctorCheck(
                layer="配置层",
                severity=Severity.ERROR,
                label=f"config.yaml 缺少 {key}",
                detail=desc,
                hint=f"在 config.yaml 中设置 {key}",
            ))
        else:
            results.append(DoctorCheck(
                layer="配置层",
                severity=Severity.INFO,
                label=f"{key}",
                detail=str(val),
            ))

    # API Key (不验证有效性, 只检查格式)
    api_key = data.get("api_key", "")
    if not api_key:
        results.append(DoctorCheck(
            layer="配置层",
            severity=Severity.WARNING,
            label="API Key 未设置",
            detail="将在首次 LLM 调用时报错",
            hint="在 config.yaml 或环境变量 DEEPSEEK_API_KEY 中设置",
        ))
    elif len(api_key) < 10:
        results.append(DoctorCheck(
            layer="配置层",
            severity=Severity.ERROR,
            label="API Key 格式异常",
            detail="长度过短",
            hint="检查 API Key 是否正确",
        ))
    else:
        masked = api_key[:6] + "…" + api_key[-4:]
        results.append(DoctorCheck(
            layer="配置层",
            severity=Severity.INFO,
            label="API Key",
            detail=masked,
        ))

    return results


def run_config_checks() -> List[DoctorCheck]:
    results = [check_config_exists()]
    results.extend(check_required_fields())
    return results
