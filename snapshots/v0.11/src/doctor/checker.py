# -*- coding: utf-8 -*-
"""
checker.py — DoctorOrchestrator

调度所有检查层, 汇总为 DoctorReport.
支持:
  - 全检 (默认)
  - --api-only (仅连接层)
  - --project <name> (特定项目)
"""

import asyncio
from datetime import datetime
from typing import Optional

from .report import DoctorReport, Severity
from .checks_env import run_env_checks
from .checks_config import run_config_checks
from .checks_api import run_api_checks
from .checks_project import run_project_checks


class DoctorOrchestrator:
    """环境诊断总调度器"""

    def __init__(self, api_only: bool = False, project: Optional[str] = None):
        self.api_only = api_only
        self.project = project

    def run(self) -> DoctorReport:
        return asyncio.run(self.run_async())

    async def run_async(self) -> DoctorReport:
        report = DoctorReport(timestamp=datetime.now().isoformat())

        if self.api_only:
            # 仅连接层
            report.checks.extend(await run_api_checks())
        else:
            # 全检: 环境 → 配置 → 连接 → 项目
            report.checks.extend(run_env_checks())
            report.checks.extend(run_config_checks())
            report.checks.extend(await run_api_checks())
            report.checks.extend(run_project_checks(self.project))

        return report
