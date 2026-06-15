# -*- coding: utf-8 -*-
"""
checks_env.py — 环境层检查

检查项:
  - Python 版本 ≥ 3.10
  - 核心 pip 依赖
  - sentence-transformers 嵌入模型缓存
  - ChromaDB 读写
"""

import sys
import tempfile
import shutil
from pathlib import Path
from typing import List

from .report import DoctorCheck, Severity


def check_python_version() -> DoctorCheck:
    v = sys.version_info
    ok = v >= (3, 10)
    return DoctorCheck(
        layer="环境层",
        severity=Severity.INFO if ok else Severity.ERROR,
        label=f"Python {v.major}.{v.minor}.{v.micro}",
        detail="✅ 版本符合" if ok else "需要 ≥ 3.10",
        hint="" if ok else "请升级 Python 至 3.10+",
    )


def check_core_packages() -> List[DoctorCheck]:
    packages = [
        ("aiohttp", "异步 HTTP 客户端（LLM 调用）"),
        ("chromadb", "向量数据库（语义检索）"),
        ("sentence_transformers", "本地嵌入模型"),
        ("yaml", "配置文件解析"),
        ("streamlit", "GUI 界面"),
    ]

    results = []
    for pkg, desc in packages:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "?")
            results.append(DoctorCheck(
                layer="环境层",
                severity=Severity.INFO,
                label=f"{pkg} ({desc})",
                detail=f"v{ver}",
            ))
        except ImportError:
            results.append(DoctorCheck(
                layer="环境层",
                severity=Severity.ERROR,
                label=f"{pkg} 未安装",
                detail=desc,
                hint=f"pip install {pkg}",
            ))
    return results


def check_embedding_model() -> DoctorCheck:
    cache_home = Path.home() / ".cache"
    candidates = [
        cache_home / "huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2",
        cache_home / "chroma/onnx_models/all-MiniLM-L6-v2",
    ]

    for path in candidates:
        if path.exists():
            model_file = next(path.rglob("*.safetensors"), None)
            if model_file:
                size_mb = model_file.stat().st_size / 1e6
                return DoctorCheck(
                    layer="环境层",
                    severity=Severity.INFO,
                    label="嵌入模型已缓存",
                    detail=f"{size_mb:.0f}MB",
                )
            return DoctorCheck(
                layer="环境层",
                severity=Severity.WARNING,
                label="嵌入模型目录存在但缺模型文件",
                hint="删除缓存目录后重新 import sentence_transformers",
            )

    return DoctorCheck(
        layer="环境层",
        severity=Severity.WARNING,
        label="嵌入模型未缓存",
        detail="首次使用将自动下载（需联网, 约 470MB）",
    )


def check_chromadb_rw() -> DoctorCheck:
    """ChromaDB 可用性检查（仅检查导入和客户端创建，不触发嵌入模型下载）"""
    try:
        import chromadb
    except ImportError:
        return DoctorCheck(
            layer="环境层",
            severity=Severity.ERROR,
            label="ChromaDB 不可用",
            detail="无法导入 chromadb",
            hint="pip install chromadb",
        )

    tmp = tempfile.mkdtemp()
    try:
        client = chromadb.PersistentClient(path=tmp)
        # 仅验证客户端能创建和心跳，不 add documents（避免触发 ONNX 模型下载）
        heartbeat_ns = client.heartbeat()
        return DoctorCheck(
            layer="环境层",
            severity=Severity.INFO,
            label="ChromaDB 可用",
            detail=f"心跳 {heartbeat_ns / 1e9:.2f}s",
        )
    except Exception as e:
        return DoctorCheck(
            layer="环境层",
            severity=Severity.ERROR,
            label="ChromaDB 初始化失败",
            detail=str(e)[:100],
            hint="检查磁盘空间和权限, 或 pip install --upgrade chromadb",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_env_checks() -> List[DoctorCheck]:
    results = [check_python_version()]
    results.extend(check_core_packages())
    results.append(check_embedding_model())
    results.append(check_chromadb_rw())
    return results
