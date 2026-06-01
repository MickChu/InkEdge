"""项目工具函数"""
from pathlib import Path


def get_project_list(projects_dir: Path = None):
    """获取所有项目列表"""
    if projects_dir is None:
        # 从调用栈推断项目根目录
        import __main__
        if hasattr(__main__, '__file__'):
            projects_dir = Path(__main__.__file__).parent / "projects"
        else:
            projects_dir = Path("projects")

    if not projects_dir.exists():
        return []

    projects = []
    for d in projects_dir.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            ch_dir = d / "chapters"
            ch_count = len(list(ch_dir.glob("*.md"))) if ch_dir.exists() else 0
            has_roles = (d / "roles.md").exists()
            has_world = (d / "world_building.md").exists()
            has_seed = (d / "core_seed.md").exists() or (d / "story_frame.md").exists()
            projects.append({
                "name": d.name,
                "has_foundation": has_seed,
                "has_roles": has_roles,
                "has_world": has_world,
                "chapter_count": ch_count,
                "path": str(d),
            })
    return sorted(projects, key=lambda p: p["name"])
