# -*- coding: utf-8 -*-
"""
InkEdge 版本发布脚本

用法:
    python release.py push      # 推送下一个未发布版本
    python release.py status    # 查看发布队列
    python release.py reset v0.10  # 重置某个版本的发布状态
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
SNAPSHOTS = ROOT / "snapshots"
QUEUE_PATH = SNAPSHOTS / "queue.json"

# Windows GBK 兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_queue() -> list:
    if not QUEUE_PATH.exists():
        return []
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def save_queue(queue: list):
    QUEUE_PATH.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_next() -> dict | None:
    """找到下一个待推送版本"""
    queue = load_queue()
    for item in queue:
        if not item.get("pushed", False):
            return item
    return None


def copy_snapshot_to_root(version: str):
    """将快照文件复制到仓库根目录"""
    src = SNAPSHOTS / version
    if not src.is_dir():
        raise FileNotFoundError(f"快照不存在: {src}")

    # 复制所有文件到根目录
    files = list(src.rglob("*"))
    copied = 0
    for f in files:
        if f.is_file():
            rel = f.relative_to(src)
            dst = ROOT / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            copied += 1
    return copied


def git_push(version: str) -> bool:
    """Git add + commit + push"""
    os.chdir(str(ROOT))

    # git add
    subprocess.run(["git", "add", "-A"], check=True, capture_output=True)

    # git commit (允许空提交失败)
    result = subprocess.run(
        ["git", "commit", "-m", f"release: {version}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            print("   (无变更，跳过 commit)")
            return False

    # git push
    result = subprocess.run(
        ["git", "push"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"   push 失败: {result.stderr[:200]}")
        return False

    print(f"   ✅ git push 成功")
    return True


def mark_pushed(version: str):
    """标记版本为已推送"""
    queue = load_queue()
    now = __import__("datetime").datetime.now().astimezone().isoformat()
    for item in queue:
        if item["version"] == version:
            item["pushed"] = True
            item["pushed_at"] = now
            break
    save_queue(queue)


# ============================================================
# 命令
# ============================================================

def cmd_push():
    """推送下一个未发布版本"""
    print("InkEdge Release — 版本推送")
    print("-" * 40)

    next_ver = find_next()
    if next_ver is None:
        print("✅ 所有版本已推送，队列为空")
        return

    version = next_ver["version"]
    print(f"📦 推送版本: {version}")

    # 1. 复制快照
    print(f"   复制快照文件...")
    n = copy_snapshot_to_root(version)
    print(f"   ✅ {n} 个文件已复制")

    # 2. Git push
    print(f"   Git push...")
    import time
    time.sleep(1)  # 让文件系统同步
    success = git_push(version)

    # 3. 标记
    if success:
        mark_pushed(version)
        print(f"\n✅ {version} 推送完成!")
    else:
        print(f"\n⚠️  {version} 代码已复制但 git 操作未完成，请手动检查")


def cmd_status():
    """查看发布队列"""
    queue = load_queue()
    print("InkEdge 发布队列")
    print("-" * 40)

    if not queue:
        print("  队列为空")
        return

    for item in queue:
        icon = "✅" if item.get("pushed") else "📦"
        extra = f" → {item.get('pushed_at', '')[:16]}" if item.get("pushed") else ""
        print(f"  {icon} {item['version']}{extra}")


def cmd_reset(version: str):
    """重置版本发布状态"""
    queue = load_queue()
    for item in queue:
        if item["version"] == version:
            item["pushed"] = False
            item.pop("pushed_at", None)
            break
    save_queue(queue)
    print(f"  🔄 {version} 已重置为待推送")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python release.py {push|status|reset <version>}")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "push":
        cmd_push()
    elif cmd == "status":
        cmd_status()
    elif cmd == "reset" and len(sys.argv) >= 3:
        cmd_reset(sys.argv[2])
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
