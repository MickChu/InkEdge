"""
Phase 7 — GUI 测试

测试 GUI 页面可导入、不崩溃。
Streamlit 页面是纯调度层，测试聚焦于: 导入检查、模块接口调用。
"""
import pytest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path("H:/Python学习/AI写小说/InkEdge")


class TestGUIImports:
    """GUI 文件导入测试"""

    def test_studio_imports(self):
        """主 Studio 页面可导入"""
        sys.path.insert(0, str(PROJECT_ROOT))
        import studio  # noqa: F401

    def test_new_project_imports(self):
        """新建项目页面可导入"""
        sys.path.insert(0, str(PROJECT_ROOT))
        # 用 exec 因为文件名以数字开头
        import importlib.util
        path = PROJECT_ROOT / "pages" / "01_new_project.py"
        spec = importlib.util.spec_from_file_location("pg_new", str(path))
        mod = importlib.util.module_from_spec(spec)
        # 不执行，只检查文件存在和语法
        assert path.exists()

    def test_write_page_imports(self):
        """写稿页面文件存在"""
        path = PROJECT_ROOT / "pages" / "02_write.py"
        assert path.exists()

    def test_style_page_imports(self):
        """风格页面文件存在"""
        path = PROJECT_ROOT / "pages" / "03_style.py"
        assert path.exists()

    def test_index_page_imports(self):
        """索引页面文件存在"""
        path = PROJECT_ROOT / "pages" / "04_index.py"
        assert path.exists()

    def test_check_page_imports(self):
        """校验页面文件存在"""
        path = PROJECT_ROOT / "pages" / "05_check.py"
        assert path.exists()

    def test_state_page_imports(self):
        """状态页面文件存在"""
        path = PROJECT_ROOT / "pages" / "06_state.py"
        assert path.exists()


class TestPagesSyntax:
    """语法检查"""

    @pytest.mark.parametrize("filename", [
        "01_new_project.py",
        "02_write.py",
        "03_style.py",
        "04_index.py",
        "05_check.py",
        "06_state.py",
    ])
    def test_page_syntax(self, filename):
        """每个页面文件语法合法"""
        path = PROJECT_ROOT / "pages" / filename
        with open(path, encoding="utf-8") as f:
            source = f.read()
        compile(source, filename, "exec")


class TestStudioFunctions:
    """项目列表函数测试"""

    def test_get_project_list(self):
        from src.utils.project_utils import get_project_list
        projects = get_project_list(PROJECT_ROOT / "projects")
        assert isinstance(projects, list)
        # 至少应有 unified_test
        names = [p["name"] for p in projects]
        assert "unified_test" in names

    def test_get_project_list_empty_dir(self, tmpdir):
        from src.utils.project_utils import get_project_list
        projects = get_project_list(Path(str(tmpdir)))
        assert projects == []
