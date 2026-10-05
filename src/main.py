"""应用入口。

启动方式：
    python run.py
    或 uvicorn src.main:app --reload --port 8000

文档地址：
    Swagger UI  http://127.0.0.1:8000/docs
    ReDoc       http://127.0.0.1:8000/redoc
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router as api_router
from src.core.config import settings
from src.core.database import init_db
from src.core.exceptions import AppError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("calculator")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时建表，避免首次请求时表不存在。"""
    init_db()
    logger.info("数据库已就绪：%s", settings.database_path)
    logger.info("允许的跨域来源：%s", settings.cors_allow_origins)
    yield
    logger.info("服务已停止")


app = FastAPI(
    title="前后端分离计算器系统 —— 后端 API",
    description=(
        "软件工程第一次作业：前后端分离计算器。\n\n"
        "所有计算均由后端完成，前端只负责输入表达式与展示结果。\n"
        "禁止使用 eval/exec，表达式由手写词法分析 + 递归下降解析器处理。"
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

# 跨域配置：前后端分离部署时前端域名与后端不同，必须显式放行
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------- 统一异常处理 ----------------------


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    """业务异常 -> 统一错误结构 + 对应状态码。"""
    logger.warning("业务异常 %s: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """请求体格式错误（缺字段、超长等）-> 422，结构与业务错误保持一致。"""
    first = exc.errors()[0] if exc.errors() else {}
    location = " -> ".join(str(part) for part in first.get("loc", []))
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "code": "VALIDATION_ERROR",
            "message": f"请求参数不合法（{location}）：{first.get('msg', '未知错误')}",
            "detail": None,
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    """兜底：未预期异常返回 500，详情只记日志不外泄。"""
    logger.exception("未处理异常：%s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误，请稍后重试",
            "detail": None,
        },
    )


# ---------------------- 路由注册 ----------------------

app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """根路径返回服务说明，避免部署后访问根域名看到 404。"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/health",
    }


# 可选：把前端构建产物挂到 /app 下，便于本地一体化预览。
# 生产环境推荐前后端分别部署，此项默认关闭。
if settings.serve_frontend and settings.frontend_dist.is_dir():
    app.mount(
        "/app",
        StaticFiles(directory=str(settings.frontend_dist), html=True),
        name="frontend",
    )
    logger.info("已挂载前端静态文件：%s -> /app", settings.frontend_dist)
