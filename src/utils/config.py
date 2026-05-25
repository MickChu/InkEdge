"""
ConfigManager — 统一配置管理

加载优先级（高到低）：
  1. 环境变量（DEEPSEEK_API_KEY 等）
  2. 项目目录下的 config.yaml
  3. 全局 config.yaml（项目根目录）
  4. 内置默认值

用法：
  from src.utils.config import config
  api_key = config.get("api_key")
  model = config.get("model_name", "deepseek-v4-flash")
"""

import os
import logging
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    # LLM 配置
    "api_key": "",
    "base_url": "https://api.deepseek.com/v1",
    "model_name": "deepseek-v4-flash",
    "interface_format": "OpenAI",
    "temperature": 0.7,
    "max_tokens": 4096,
    "timeout": 600,

    # 回退模型
    "fallback_models": ["deepseek-chat"],

    # Embedding 由 VectorStore 本地 sentence-transformers 处理，无需 API
    "embedding_retrieval_k": 4,

    # 小说默认参数
    "default_genre": "奇幻",
    "default_chapters": 60,
    "default_words_per_chapter": 3000,
    "default_template": "snowflake",

    # 世界观深度控制
    "worldbuilding_depth": "standard",  # minimal / standard / deep
}

# 环境变量映射
ENV_MAP = {
    "api_key": ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"],
    "base_url": ["DEEPSEEK_BASE_URL", "OPENAI_BASE_URL"],

}


class ConfigManager:
    """配置管理器"""

    def __init__(self, project_dir: Optional[str] = None):
        self._env_config = self._load_env()
        self._file_config = self._load_yaml_configs(project_dir)
        self._cache: dict = {}
        log.debug(f"ConfigManager initialized (env={len(self._env_config)}, file={len(self._file_config)})")

    def _load_env(self) -> dict:
        """从环境变量加载"""
        result = {}
        for key, env_vars in ENV_MAP.items():
            for var in env_vars:
                val = os.environ.get(var, "")
                if val:
                    result[key] = val
                    break
        return result

    def _load_yaml_configs(self, project_dir: Optional[str] = None) -> dict:
        """加载 YAML 配置文件"""
        import yaml

        candidates = []

        # 项目级配置
        if project_dir:
            candidates.append(Path(project_dir) / "config.yaml")

        # 全局配置（项目根目录）
        root_config = Path(__file__).parent.parent.parent / "config.yaml"
        candidates.append(root_config)

        # 用户目录配置
        home_config = Path.home() / ".inkedge" / "config.yaml"
        candidates.append(home_config)

        result = {}
        for path in candidates:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                    result.update(data)
                    log.debug(f"Loaded config: {path}")
                except Exception as e:
                    log.warning(f"Failed to load {path}: {e}")

        return result

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（已缓存）"""
        if key in self._cache:
            return self._cache[key]

        # 优先级：env > file > default
        if key in self._env_config and self._env_config[key]:
            val = self._env_config[key]
        elif key in self._file_config:
            val = self._file_config[key]
        else:
            val = DEFAULT_CONFIG.get(key, default)

        self._cache[key] = val
        return val

    def set(self, key: str, value: Any) -> None:
        """设置运行时配置（不持久化）"""
        self._cache[key] = value

    def all(self) -> dict:
        """获取所有配置"""
        result = {**DEFAULT_CONFIG, **self._file_config, **self._env_config, **self._cache}
        return result

    def mask_sensitive(self, d: dict) -> dict:
        """脱敏敏感字段"""
        result = dict(d)
        for k in ("api_key",):
            if k in result and result[k]:
                val = result[k]
                if len(val) > 8:
                    result[k] = val[:4] + "…" + val[-4:]
                else:
                    result[k] = "***"
        return result

    def save_to_file(self, path: str, updates: dict) -> None:
        """将更新写入 YAML 文件（合并模式）"""
        import yaml

        existing = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = yaml.safe_load(f) or {}
            except Exception:
                pass

        existing.update(updates)
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(existing, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        # 更新内存中的文件配置
        self._file_config.update(updates)
        log.info(f"Config saved to {path}")


# 全局模块级实例（延迟初始化）
_config_instance: Optional[ConfigManager] = None


def get_config(project_dir: Optional[str] = None) -> ConfigManager:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager(project_dir)
    return _config_instance


# 便捷别名
config = get_config()
