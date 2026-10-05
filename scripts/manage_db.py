"""开发辅助脚本：初始化数据库、查看历史、清空历史。

用法：
    python scripts/manage_db.py init      建表
    python scripts/manage_db.py show      打印最近 10 条历史
    python scripts/manage_db.py clear     清空历史
"""

from __future__ import annotations

import sys
from pathlib import Path

# 允许以 `python scripts/manage_db.py` 方式直接运行
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import settings  # noqa: E402
from src.core.database import init_db  # noqa: E402
from src.repository import history_repository as repo  # noqa: E402


def cmd_init() -> None:
    init_db()
    print(f"[OK] 数据库已初始化：{settings.database_path}")


def cmd_show() -> None:
    records = repo.list_history(limit=10, offset=0)
    if not records:
        print("（暂无历史记录）")
        return
    print(f"{'ID':>4}  {'表达式':<22} {'结果':<18} 时间")
    print("-" * 72)
    for item in records:
        print(
            f"{item['id']:>4}  {item['expression']:<22} "
            f"{item['result']:<18} {item['created_at']}"
        )
    print(f"\n共 {repo.count_history()} 条记录")


def cmd_clear() -> None:
    count = repo.clear_history()
    print(f"[OK] 已清空 {count} 条历史记录")


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "init"
    actions = {"init": cmd_init, "show": cmd_show, "clear": cmd_clear}
    action = actions.get(command)
    if action is None:
        print(__doc__)
        raise SystemExit(1)
    action()


if __name__ == "__main__":
    main()
