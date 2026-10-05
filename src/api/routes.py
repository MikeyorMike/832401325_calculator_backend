"""HTTP 路由定义。

接口清单
    GET    /api/health                 健康检查
    POST   /api/calculate              计算表达式并落库
    GET    /api/history                分页查询历史
    GET    /api/history/{id}           查询单条历史
    DELETE /api/history/{id}           删除指定历史
    DELETE /api/history                清空全部历史（扩展）
    PATCH  /api/history/{id}/favorite  切换收藏（扩展）
    GET    /api/statistics             统计信息（扩展）

设计原则：
    路由函数只负责「解析参数 -> 调用业务层 -> 组装响应」，
    不含任何计算逻辑或 SQL，保证分层清晰。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Path, Query, status

from src.api import schemas
from src.core.exceptions import ExpressionError, RecordNotFoundError
from src.repository import history_repository as repo
from src.service import extended_service, history_service

router = APIRouter(prefix="/api", tags=["calculator"])


@router.get(
    "/health",
    response_model=schemas.HealthResponse,
    summary="健康检查",
    description="用于确认后端服务是否存活，部署后可直接在浏览器中访问。",
)
def health_check() -> schemas.HealthResponse:
    from src.core.config import settings

    return schemas.HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
    )


@router.post(
    "/calculate",
    response_model=schemas.CalculateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="计算表达式",
    description=(
        "后端完成校验、解析、计算与落库，返回结果。"
        "表达式非法或除数为零时返回 400。"
    ),
    responses={
        400: {"model": schemas.ErrorResponse, "description": "表达式非法"},
        422: {"model": schemas.ErrorResponse, "description": "请求体格式错误"},
    },
)
def calculate(payload: schemas.CalculateRequest) -> schemas.CalculateResponse:
    outcome = history_service.calculate_and_save(
        payload.expression, is_extended=payload.is_extended
    )
    return schemas.CalculateResponse(
        expression=str(outcome["expression"]),
        normalized=str(outcome["normalized"]),
        result=str(outcome["result"]),
        record=schemas.HistoryRecord(**outcome["record"]),
    )


@router.get(
    "/history",
    response_model=schemas.HistoryListResponse,
    summary="查询计算历史",
    description="按时间倒序分页返回历史记录，支持关键字搜索与仅看收藏。",
)
def get_history(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    keyword: str | None = Query(default=None, max_length=50, description="搜索关键字"),
    favorites_only: bool = Query(default=False, description="仅返回已收藏记录"),
) -> schemas.HistoryListResponse:
    data = history_service.list_history(
        page=page, page_size=page_size, keyword=keyword, favorites_only=favorites_only
    )
    return schemas.HistoryListResponse(
        items=[schemas.HistoryItem(**item) for item in data["items"]],
        page=int(data["page"]),
        page_size=int(data["page_size"]),
        total=int(data["total"]),
        total_pages=int(data["total_pages"]),
    )


@router.get(
    "/history/{record_id}",
    response_model=schemas.HistoryItem,
    summary="查询单条历史",
    responses={404: {"model": schemas.ErrorResponse, "description": "记录不存在"}},
)
def get_history_item(
    record_id: int = Path(..., ge=1, description="历史记录 ID"),
) -> schemas.HistoryItem:
    record = repo.get_history_by_id(record_id)
    if record is None:
        raise RecordNotFoundError(f"历史记录不存在：id={record_id}")
    return schemas.HistoryItem(**record)


@router.delete(
    "/history/{record_id}",
    response_model=schemas.DeleteResponse,
    summary="删除指定历史记录",
    description="从数据库中真实删除该记录。",
    responses={404: {"model": schemas.ErrorResponse, "description": "记录不存在"}},
)
def delete_history_item(
    record_id: int = Path(..., ge=1, description="历史记录 ID"),
) -> schemas.DeleteResponse:
    history_service.delete_history(record_id)
    return schemas.DeleteResponse(
        message=f"已删除历史记录 id={record_id}", deleted_id=record_id
    )


@router.delete(
    "/history",
    response_model=schemas.DeleteResponse,
    summary="清空全部历史（扩展功能）",
)
def clear_history() -> schemas.DeleteResponse:
    count = history_service.clear_history()
    return schemas.DeleteResponse(
        message=f"已清空全部历史记录，共 {count} 条", deleted_count=count
    )


@router.patch(
    "/history/{record_id}/favorite",
    response_model=schemas.FavoriteResponse,
    summary="切换收藏状态（扩展功能）",
    responses={404: {"model": schemas.ErrorResponse, "description": "记录不存在"}},
)
def toggle_favorite(
    record_id: int = Path(..., ge=1, description="历史记录 ID"),
) -> schemas.FavoriteResponse:
    record = history_service.toggle_favorite(record_id)
    return schemas.FavoriteResponse(record=schemas.HistoryItem(**record))


@router.get(
    "/statistics",
    response_model=schemas.StatisticsResponse,
    summary="计算统计（扩展功能）",
)
def statistics() -> schemas.StatisticsResponse:
    data = history_service.get_statistics()
    return schemas.StatisticsResponse(**data)


# ============================================================
# 扩展功能（加分项）：科学计算 / 进制转换 / 单位换算
# ============================================================


@router.post(
    "/extended",
    response_model=schemas.ExtendedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="扩展功能计算（加分项）",
    description=(
        "统一入口处理科学计算、进制转换与单位换算。"
        "运算同样在后端完成，结果一并写入计算历史。"
    ),
    responses={400: {"model": schemas.ErrorResponse, "description": "参数非法"}},
)
def extended_calculate(payload: schemas.ExtendedRequest) -> schemas.ExtendedResponse:
    if payload.type == "scientific":
        if not payload.function:
            raise ExpressionError("科学计算必须提供 function 参数")
        outcome = extended_service.calculate_scientific(
            payload.function, payload.operands
        )
    elif payload.type == "base":
        if payload.value is None or payload.from_base is None or payload.to_base is None:
            raise ExpressionError("进制转换必须提供 value、from_base、to_base")
        outcome = extended_service.convert_base(
            payload.value, payload.from_base, payload.to_base
        )
    else:
        if (
            payload.value is None
            or not payload.category
            or not payload.from_unit
            or not payload.to_unit
        ):
            raise ExpressionError(
                "单位换算必须提供 value、category、from_unit、to_unit"
            )
        outcome = extended_service.convert_unit(
            payload.category, payload.value, payload.from_unit, payload.to_unit
        )

    # 扩展功能的计算同样写入历史记录，标记 is_extended=True 便于分类展示
    record = repo.insert_history(
        expression=str(outcome["expression"]),
        result=str(outcome["result"]),
        created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        is_extended=True,
    )

    return schemas.ExtendedResponse(
        type=payload.type,
        display=str(outcome["display"]),
        result=str(outcome["result"]),
        expression=str(outcome["expression"]),
        record=schemas.HistoryRecord(**record),
    )


@router.get(
    "/extended/capabilities",
    summary="扩展功能能力清单",
    description="返回可选的科学函数、支持进制与单位，前端据此渲染下拉框。",
)
def extended_capabilities() -> dict[str, object]:
    return {
        "success": True,
        "scientific_functions": [
            {"name": name, "label": extended_service.FUNCTION_LABELS[name], "arity": arity}
            for name, (arity, _) in sorted(
                extended_service.SCIENTIFIC_FUNCTIONS.items()
            )
        ],
        "bases": [
            {"value": base, "label": label}
            for base, label in extended_service.BASE_NAMES.items()
        ],
        "unit_categories": [
            {
                "name": category,
                "label": extended_service.CATEGORY_LABELS[category],
                "units": [
                    {"name": unit, "label": label}
                    for unit, label in extended_service.UNIT_LABELS[category].items()
                ],
            }
            for category in extended_service.UNIT_LABELS
        ],
    }
