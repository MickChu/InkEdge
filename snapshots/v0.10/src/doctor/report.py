# -*- coding: utf-8 -*-
"""
report.py — Doctor 检查结果数据类 + 格式化输出

DoctorCheck   : 单项检查结果
DoctorReport  : 汇总报告, 支持 CLI/JSON 两种输出
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"      # 核心功能不可用, 必须先修
    WARNING = "warning"  # 部分功能受限, 建议修
    INFO = "info"        # 纯信息, 无需处理


@dataclass
class DoctorCheck:
    """单项检查结果"""
    layer: str          # 环境层/配置层/连接层/项目层
    severity: Severity
    label: str          # 检查项名称
    detail: str = ""    # 详细信息
    hint: str = ""      # 修复建议

    @property
    def icon(self) -> str:
        if self.severity == Severity.ERROR:
            return "❌"
        elif self.severity == Severity.WARNING:
            return "⚠️ "
        else:
            return "✅"

    def format_cli(self) -> str:
        line = f"  {self.icon} {self.label}"
        if self.detail:
            line += f" ({self.detail})"
        if self.hint:
            line += f"\n     💡 {self.hint}"
        return line


@dataclass
class DoctorReport:
    """汇总检查报告"""
    checks: List[DoctorCheck] = field(default_factory=list)
    timestamp: str = ""

    def add(self, layer: str, severity: Severity, label: str,
            detail: str = "", hint: str = ""):
        self.checks.append(DoctorCheck(
            layer=layer, severity=severity,
            label=label, detail=detail, hint=hint,
        ))

    @property
    def errors(self) -> List[DoctorCheck]:
        return [c for c in self.checks if c.severity == Severity.ERROR]

    @property
    def warnings(self) -> List[DoctorCheck]:
        return [c for c in self.checks if c.severity == Severity.WARNING]

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def healthy(self) -> bool:
        return not self.has_errors()

    # ============================================================
    # CLI 格式化输出
    # ============================================================

    def format_cli(self) -> str:
        lines = []
        lines.append("")
        lines.append("🩺 InkEdge Doctor")
        lines.append("━" * 55)

        # 按层分组输出
        layer_order = ["环境层", "配置层", "连接层", "项目层"]
        layers = {l: [] for l in layer_order}
        for c in self.checks:
            if c.layer in layers:
                layers[c.layer].append(c)

        for layer_name in layer_order:
            items = layers[layer_name]
            if not items:
                continue
            lines.append(f"\n  {layer_name}")
            for c in items:
                lines.append(c.format_cli())

        # 统计
        lines.append(f"\n{'━' * 55}")
        n_err = len(self.errors)
        n_warn = len(self.warnings)
        if n_err == 0 and n_warn == 0:
            lines.append("  🎉 全部通过!")
            lines.append(f"  0 个错误  0 个警告")
        else:
            status = "✅ 环境就绪" if n_err == 0 else "❌ 存在问题"
            lines.append(f"  {status}")
            lines.append(f"  {n_err} 个错误  {n_warn} 个警告")
        lines.append("")

        return "\n".join(lines)

    # ============================================================
    # JSON 输出（供脚本调用）
    # ============================================================

    def to_json(self) -> dict:
        return {
            "healthy": self.healthy,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "timestamp": self.timestamp,
            "checks": [
                {
                    "layer": c.layer,
                    "severity": c.severity.value,
                    "label": c.label,
                    "detail": c.detail,
                    "hint": c.hint,
                }
                for c in self.checks
            ],
        }

    # ============================================================
    # --fix 自动修复
    # ============================================================

    def auto_fix(self) -> int:
        """尝试自动修复简单问题, 返回修复数量"""
        fixed = 0
        # 创建缺失的 projects/ 目录
        from pathlib import Path
        projects_dir = Path("projects")
        if not projects_dir.exists():
            projects_dir.mkdir()
            fixed += 1

        # 生成模板 config.yaml
        config_path = Path("config.yaml")
        if not config_path.exists():
            template = (
                "# InkEdge 配置文件\n"
                "api_key: 【在此填入你的API Key】\n"
                "base_url: https://api.deepseek.com/v1\n"
                "model_name: deepseek-v4-flash\n"
                "interface_format: OpenAI\n"
                "temperature: 0.7\n"
                "max_tokens: 8192\n"
                "timeout: 600\n"
                "fallback_models:\n"
                "  - deepseek-chat\n"
                "embedding_retrieval_k: 4\n"
                "default_genre: 奇幻\n"
                "default_chapters: 60\n"
                "default_words_per_chapter: 3000\n"
                "default_template: unified\n"
                "worldbuilding_depth: standard\n"
            )
            config_path.write_text(template, encoding="utf-8")
            fixed += 1

        return fixed
