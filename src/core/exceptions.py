"""统一异常体系。

设计思路：
    业务层只抛出带错误码的领域异常，接口层负责把它们翻译成
    HTTP 状态码 + 统一 JSON 结构，避免异常信息直接泄露到客户端。
"""

from __future__ import annotations


class AppError(Exception):
    """所有业务异常的基类。

    Attributes:
        code: 机器可读的错误码，前端据此做差异化提示。
        message: 面向用户的错误说明。
        status_code: 对应的 HTTP 状态码。
    """

    code: str = "APP_ERROR"
    status_code: int = 500

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class ExpressionError(AppError):
    """表达式非法（语法错误、非法字符、括号不匹配等）。"""

    code = "INVALID_EXPRESSION"
    status_code = 400


class DivisionByZeroError(ExpressionError):
    """除数为零。"""

    code = "DIVISION_BY_ZERO"
    status_code = 400


class ExpressionTooLongError(ExpressionError):
    """表达式超出长度上限。"""

    code = "EXPRESSION_TOO_LONG"
    status_code = 400


class ResultOverflowError(ExpressionError):
    """计算结果溢出（超出可表示范围）。"""

    code = "RESULT_OVERFLOW"
    status_code = 400


class RecordNotFoundError(AppError):
    """指定的历史记录不存在。"""

    code = "RECORD_NOT_FOUND"
    status_code = 404


class DatabaseError(AppError):
    """数据库操作失败。"""

    code = "DATABASE_ERROR"
    status_code = 500
