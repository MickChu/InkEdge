"""
file_io — 原子文件读写工具
"""

import os
import tempfile
import logging

log = logging.getLogger(__name__)


def ensure_dir(path: str) -> str:
    """确保目录存在，返回路径"""
    os.makedirs(path, exist_ok=True)
    return path


def read_file(filepath: str, default: str = "") -> str:
    """安全读取文件，不存在则返回 default"""
    try:
        if not os.path.exists(filepath):
            return default
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        log.warning(f"读取文件失败 {filepath}: {e}")
        return default


def write_file(filepath: str, content: str, atomic: bool = True) -> bool:
    """
    写入文件。
    atomic=True 时使用临时文件 + rename 保证原子性。
    """
    try:
        ensure_dir(os.path.dirname(filepath))
        if atomic:
            fd, tmp_path = tempfile.mkstemp(
                suffix=".tmp", dir=os.path.dirname(filepath)
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp_path, filepath)
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        return True
    except Exception as e:
        log.error(f"写入文件失败 {filepath}: {e}")
        return False
