# -*- coding: utf-8 -*-
"""
checks_project.py — 项目层检查

检查项:
  - projects/ 目录存在
  - 项目数统计
  - 各项目核心文件完整性
  - ChromaDB 索引状态
"""

from pathlib import Path
from typing import List

from .report import DoctorCheck, Severity


CORE_FILES = ["story_frame.md", "roles.md", "book_rules.md", "volume_map.md"]


def check_projects_dir() -> DoctorCheck:
    p = Path("projects")
    if not p.exists():
        return DoctorCheck(
            layer="项目层",
            severity=Severity.WARNING,
            label="projects/ 目录不存在",
            detail="尚未创建任何项目",
            hint='运行 python main.py new --name "书名"',
        )

    proj_dirs = [d for d in p.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
    if not proj_dirs:
        return DoctorCheck(
            layer="项目层",
            severity=Severity.INFO,
            label="projects/ 存在",
            detail="无项目（空目录）",
        )

    return DoctorCheck(
        layer="项目层",
        severity=Severity.INFO,
        label="projects/ 存在",
        detail=f"{len(proj_dirs)} 个项目",
    )


def check_project_integrity(project_name: str = None) -> List[DoctorCheck]:
    results = []
    p = Path("projects")
    if not p.exists():
        return results

    proj_dirs = [d for d in p.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))]
    if project_name:
        proj_dirs = [d for d in proj_dirs if d.name == project_name]

    for proj in proj_dirs:
        # 核心文件检查
        missing = [f for f in CORE_FILES if not (proj / f).exists()]
        alt_missing = []
        if missing:
            # 兼容旧目录结构: foundation/ 或 story/ 子目录
            for alt_dir in ["foundation", "story"]:
                alt = proj / alt_dir
                if alt.exists():
                    still = [f for f in missing if not (alt / f).exists()]
                    alt_missing = still
                    break

        if alt_missing:
            results.append(DoctorCheck(
                layer="项目层",
                severity=Severity.WARNING,
                label=f"项目 {proj.name} 缺少核心文件",
                detail=f"缺失: {', '.join(alt_missing)}",
                hint=f"运行 python main.py new --name \"{proj.name}\" 重新生成",
            ))
        else:
            results.append(DoctorCheck(
                layer="项目层",
                severity=Severity.INFO,
                label=f"📖 {proj.name}",
                detail="核心文件齐全",
            ))

        # 章节统计
        ch_dir = proj / "chapters"
        if ch_dir.exists():
            chapters = sorted([f.name for f in ch_dir.iterdir()
                               if f.suffix in (".md", ".txt")])
            if chapters:
                results.append(DoctorCheck(
                    layer="项目层",
                    severity=Severity.INFO,
                    label=f"  已写章节",
                    detail=f"{len(chapters)} 章 ({chapters[0]} ~ {chapters[-1]})",
                ))

        # ChromaDB 索引状态（轻量检查，不触发模型下载）
        chroma_dir = proj / ".chroma"
        if chroma_dir.exists():
            sqlite = chroma_dir / "chroma.sqlite3"
            if sqlite.exists():
                size_kb = sqlite.stat().st_size // 1024
                results.append(DoctorCheck(
                    layer="项目层",
                    severity=Severity.INFO,
                    label=f"  向量索引",
                    detail=f"chroma.sqlite3 ({size_kb}KB)",
                ))
            else:
                results.append(DoctorCheck(
                    layer="项目层",
                    severity=Severity.WARNING,
                    label=f"  向量索引异常",
                    detail=".chroma 存在但缺 sqlite",
                    hint="删除 .chroma 后重新 index",
                ))
        else:
            results.append(DoctorCheck(
                layer="项目层",
                severity=Severity.INFO,
                label=f"  向量索引",
                detail="未构建",
                hint=f'运行 python main.py index --name "{proj.name}" 以启用语义检索',
            ))

    return results


def run_project_checks(project_name: str = None) -> List[DoctorCheck]:
    results = [check_projects_dir()]
    results.extend(check_project_integrity(project_name))
    return results
