"""计算历史的数据库读写（单表 CRUD）。

隔离这一层的价值：
    业务层只调用语义化的函数（insert_history / delete_history），
    换数据库或改表结构时只需修改本文件。
"""

from __future__ import annotations

from typing import Any

from src.core.database import get_connection

# 统一列顺序，避免 SELECT * 带来的隐患
_COLUMNS = "id, expression, result, created_at, is_favorite, is_extended"


def _row_to_dict(row: Any) -> dict[str, Any]:
    """把 sqlite3.Row 转成普通字典（id 之外的布尔字段还原成 bool）。"""
    return {
        "id": row["id"],
        "expression": row["expression"],
        "result": row["result"],
        "created_at": row["created_at"],
        "is_favorite": bool(row["is_favorite"]),
        "is_extended": bool(row["is_extended"]),
    }


def _build_filters(
    keyword: str | None, favorites_only: bool
) -> tuple[str, list[Any]]:
    """构造 WHERE 子句与参数列表（参数化查询，防 SQL 注入）。"""
    clauses: list[str] = []
    params: list[Any] = []

    if keyword:
        clauses.append("(expression LIKE ? OR result LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like])

    if favorites_only:
        clauses.append("is_favorite = 1")

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


def insert_history(
    *,
    expression: str,
    result: str,
    created_at: str,
    is_extended: bool = False,
) -> dict[str, Any]:
    """插入一条计算记录并返回完整记录（含自增 id）。"""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO calculation_history
                (expression, result, created_at, is_extended)
            VALUES (?, ?, ?, ?)
            """,
            (expression, result, created_at, 1 if is_extended else 0),
        )
        new_id = int(cursor.lastrowid or 0)
        row = connection.execute(
            f"SELECT {_COLUMNS} FROM calculation_history WHERE id = ?",
            (new_id,),
        ).fetchone()

    if row is None:  # pragma: no cover - 插入后必然可查到
        raise RuntimeError("插入历史记录后无法读取该记录")
    return _row_to_dict(row)


def list_history(
    *,
    limit: int,
    offset: int,
    keyword: str | None = None,
    favorites_only: bool = False,
) -> list[dict[str, Any]]:
    """按时间倒序分页查询，支持关键字与收藏筛选。"""
    where, params = _build_filters(keyword, favorites_only)
    sql = (
        f"SELECT {_COLUMNS} FROM calculation_history"
        f"{where} ORDER BY id DESC LIMIT ? OFFSET ?"
    )
    with get_connection() as connection:
        rows = connection.execute(sql, [*params, limit, offset]).fetchall()
    return [_row_to_dict(row) for row in rows]


def count_history(
    *, keyword: str | None = None, favorites_only: bool = False
) -> int:
    """统计符合条件的记录数，用于分页。"""
    where, params = _build_filters(keyword, favorites_only)
    with get_connection() as connection:
        row = connection.execute(
            f"SELECT COUNT(*) AS total FROM calculation_history{where}",
            params,
        ).fetchone()
    return int(row["total"]) if row else 0


def record_exists(record_id: int) -> bool:
    """判断记录是否存在。"""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM calculation_history WHERE id = ? LIMIT 1",
            (record_id,),
        ).fetchone()
    return row is not None


def get_history_by_id(record_id: int) -> dict[str, Any] | None:
    """按主键查询单条记录；不存在时返回 None。"""
    with get_connection() as connection:
        row = connection.execute(
            f"SELECT {_COLUMNS} FROM calculation_history WHERE id = ?",
            (record_id,),
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def delete_history(record_id: int) -> None:
    """删除指定记录。"""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM calculation_history WHERE id = ?", (record_id,)
        )


def clear_history() -> int:
    """清空整表，返回删除条数。"""
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM calculation_history")
        return int(cursor.rowcount or 0)


def toggle_favorite(record_id: int) -> dict[str, Any]:
    """翻转收藏标记并返回更新后的记录。"""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE calculation_history
               SET is_favorite = CASE is_favorite WHEN 1 THEN 0 ELSE 1 END
             WHERE id = ?
            """,
            (record_id,),
        )
        row = connection.execute(
            f"SELECT {_COLUMNS} FROM calculation_history WHERE id = ?",
            (record_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError(f"更新收藏状态后无法读取记录：id={record_id}")
    return _row_to_dict(row)


def count_by_date_prefix(date_prefix: str) -> int:
    """统计某一天（按 ISO 日期前缀匹配）产生的记录数。"""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
              FROM calculation_history
             WHERE created_at LIKE ?
            """,
            (f"{date_prefix}%",),
        ).fetchone()
    return int(row["total"]) if row else 0


def get_latest_created_at() -> str | None:
    """最近一次计算时间；无记录时返回 None。"""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT MAX(created_at) AS latest FROM calculation_history"
        ).fetchone()
    return row["latest"] if row and row["latest"] else None
