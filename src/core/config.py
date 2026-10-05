"""应用配置。

所有可变项都通过环境变量注入，默认值面向本地开发，
部署到云平台时只需设置环境变量即可，无需改代码。
"""

from __future__ import annotations

import os
from pathlib import Path

# 项目根目录：本文件位于 <root>/src/core/config.py，向上三级即根目录
BASE_DIR: Path = Path(__file__).resolve().parents[2]


def _split_env_list(raw: str) -> list[str]:
    """把逗号分隔的环境变量拆成列表，并去掉空白项。"""
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """集中管理运行期配置。"""

    def __init__(self) -> None:
        # ---------- 应用元信息 ----------
        self.app_name: str = "Calculator Backend"
        self.app_version: str = "1.0.0"

        # ---------- 数据库 ----------
        default_db = BASE_DIR / "data" / "calculator.db"
        self.database_path: Path = Path(
            os.getenv("DATABASE_PATH", str(default_db))
        ).resolve()

        # ---------- 跨域 ----------
        # 前端与后端不同源，浏览器会拦截跨域请求，必须显式放行前端来源。
        # 默认 "*" 便于本地联调；生产环境建议设置成具体的前端域名。
        raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
        self.cors_allow_origins: list[str] = _split_env_list(raw_origins) or ["*"]

        # ---------- 业务参数 ----------
        # 表达式最大长度：防止超长输入造成资源消耗
        self.max_expression_length: int = int(
            os.getenv("MAX_EXPRESSION_LENGTH", "200")
        )
        # 高精度计算有效位数：Decimal 上下文的 prec
        self.decimal_precision: int = int(os.getenv("DECIMAL_PRECISION", "28"))
        # 计算结果的绝对值超过该阈值时判定为溢出，直接报错而不是返回 Infinity
        # 用字符串保存（如 "1e100"），由业务层转成 Decimal 比较
        self.max_result_magnitude: str = os.getenv(
            "MAX_RESULT_MAGNITUDE", "1e100"
        )
        # 单页最多返回多少条历史
        self.max_page_size: int = int(os.getenv("MAX_PAGE_SIZE", "100"))

        # ---------- 前端静态文件（可选，仅用于本地一体化预览） ----------
        self.serve_frontend: bool = (
            os.getenv("SERVE_FRONTEND", "false").lower() == "true"
        )
        self.frontend_dist: Path = Path(
            os.getenv("FRONTEND_DIST", str(BASE_DIR / "static"))
        ).resolve()

    def ensure_directories(self) -> None:
        """确保数据库所在目录存在。"""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)


# 全局唯一配置实例
settings = Settings()
