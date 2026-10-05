"""业务层 —— 计算历史（查询 / 保存 / 删除 / 统计 / 收藏）。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.exceptions import RecordNotFoundError
from src.repository import history_repository as repo
from src.service.calculator import evaluate


def calculate_and_save(raw_expression: str, *, is_extended: bool = False) -> dict[str, Any]:
    """计算表达式并把成功结果写入数据库。

    流程（对应作业要求的标准链路）：
        前端传表达式 -> 后端校验 -> 后端解析 -> 后端计算
        -> 后端落库 -> 后端返回结果 -> 前端展示

    注意：只有在计算成功后才落库，非法表达式不会被记录。
    """
    outcome = evaluate(raw_expression)
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")

    record = repo.insert_history(
        expression=str(outcome["normalized"]),
        result=str(outcome["result"]),
        created_at=created_at,
        is_extended=is_extended,
    )

    return {
        "expression": outcome["expression"],
        "normalized": outcome["normalized"],
        "result": outcome["result"],
        "record": record,
    }


def list_history(
    *,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    favorites_only: bool = False,
) -> dict[str, Any]:
    """分页查询历史记录（扩展功能：关键字搜索 + 收藏筛选）。"""
    offset = (page - 1) * page_size
    items = repo.list_history(
        limit=page_size,
        offset=offset,
        keyword=keyword,
        favorites_only=favorites_only,
    )
    total = repo.count_history(keyword=keyword, favorites_only=favorites_only)
    total_pages = (total + page_size - 1) // page_size if total else 0

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def delete_history(record_id: int) -> None:
    """删除指定历史记录；记录不存在时抛 404 领域异常。"""
    if not repo.record_exists(record_id):
        raise RecordNotFoundError(f"历史记录不存在：id={record_id}")
    repo.delete_history(record_id)


def clear_history() -> int:
    """清空全部历史，返回删除条数。"""
    return repo.clear_history()


def toggle_favorite(record_id: int) -> dict[str, Any]:
    """切换收藏状态（扩展功能）。"""
    if not repo.record_exists(record_id):
        raise RecordNotFoundError(f"历史记录不存在：id={record_id}")
    return repo.toggle_favorite(record_id)


def get_statistics() -> dict[str, Any]:
    """统计信息（扩展功能）：总数、收藏数、今日新增、最近一次计算时间。"""
    today_prefix = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    return {
        "total": repo.count_history(),
        "favorites": repo.count_history(favorites_only=True),
        "today": repo.count_by_date_prefix(today_prefix),
        "latest_at": repo.get_latest_created_at(),
    }
