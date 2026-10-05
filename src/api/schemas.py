"""请求 / 响应数据模型（Pydantic v2）。

这一层的作用：
    1. 自动校验前端传来的 JSON 结构，缺字段或类型错误直接返回 422；
    2. 自动生成 OpenAPI 文档（/docs），方便助教查看接口定义；
    3. 把「接口契约」显式写进代码，前后端对接有据可依。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from src.core.config import settings


class CalculateRequest(BaseModel):
    """计算请求体：``{"expression": "(1+2)*3"}``。"""

    expression: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_expression_length,
        description="待计算的数学表达式",
        examples=["(1+2)*3"],
    )
    is_extended: bool = Field(
        default=False,
        description="是否来自扩展功能（科学计算 / 进制转换等），仅用于分类展示",
    )

    @field_validator("expression")
    @classmethod
    def _strip_expression(cls, value: str) -> str:
        """去掉首尾空白，避免纯空格输入被当成合法表达式。"""
        stripped = value.strip()
        if not stripped:
            raise ValueError("表达式不能为空")
        return stripped


class HistoryRecord(BaseModel):
    """单条历史记录。"""

    id: int
    expression: str
    result: str
    created_at: str
    is_favorite: bool = False
    is_extended: bool = False


class CalculateResponse(BaseModel):
    """计算成功响应。"""

    success: bool = True
    expression: str
    normalized: str
    result: str
    record: HistoryRecord


class ErrorResponse(BaseModel):
    """失败响应：所有错误都遵循同一结构。"""

    success: bool = False
    code: str
    message: str
    detail: str | None = None


class HistoryItem(BaseModel):
    """历史查询返回的单条数据。"""

    id: int
    expression: str
    result: str
    created_at: str
    is_favorite: bool = False
    is_extended: bool = False


class HistoryListResponse(BaseModel):
    """历史分页查询响应。"""

    success: bool = True
    items: list[HistoryItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class DeleteResponse(BaseModel):
    """删除成功响应。"""

    success: bool = True
    message: str
    deleted_id: int | None = None
    deleted_count: int | None = None


class FavoriteResponse(BaseModel):
    """收藏切换响应。"""

    success: bool = True
    record: HistoryItem


class StatisticsResponse(BaseModel):
    """统计信息响应（扩展功能）。"""

    success: bool = True
    total: int
    favorites: int
    today: int
    latest_at: str | None = None


class HealthResponse(BaseModel):
    """健康检查响应，部署后用于确认后端是否存活。"""

    success: bool = True
    status: str
    app: str
    version: str


# ============================================================
# 扩展功能（加分项）
# ============================================================


class ExtendedRequest(BaseModel):
    """扩展功能统一请求体。

    type 取值：
        scientific  —— 科学计算，需提供 function 与 operands
        base        —— 进制转换，需提供 value / from_base / to_base
        unit        —— 单位换算，需提供 category / value / from_unit / to_unit
    """

    type: Literal["scientific", "base", "unit"] = Field(
        ..., description="扩展功能类型"
    )
    # scientific
    function: str | None = Field(default=None, max_length=32)
    operands: list[str] = Field(default_factory=list, max_length=4)
    # base / unit
    value: str | None = Field(default=None, max_length=64)
    from_base: int | None = Field(default=None, ge=2, le=16)
    to_base: int | None = Field(default=None, ge=2, le=16)
    category: str | None = Field(default=None, max_length=16)
    from_unit: str | None = Field(default=None, max_length=16)
    to_unit: str | None = Field(default=None, max_length=16)

    @field_validator("operands")
    @classmethod
    def _check_operands(cls, value: list[str]) -> list[str]:
        """限制单个操作数长度，防止超长数字串拖慢计算。"""
        for item in value:
            if len(item) > 64:
                raise ValueError("单个操作数长度不能超过 64 个字符")
        return value


class ExtendedResponse(BaseModel):
    """扩展功能响应。"""

    success: bool = True
    type: str
    display: str
    result: str
    expression: str
    record: HistoryRecord | None = None
