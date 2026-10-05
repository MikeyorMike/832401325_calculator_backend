"""表达式解析与求值引擎（本项目的核心模块）。

================================================================
设计要点
================================================================

1. 为什么不用 eval / exec？
   eval 会把用户输入当作**程序代码**执行，攻击者可以构造
   ``__import__('os').system('rm -rf /')`` 之类的表达式。
   作业明确禁止使用。因此这里手写「词法分析 + 递归下降语法分析」，
   用户输入只可能被解释为数字和四则运算符，非法输入直接报错。

2. 整体流程
      原始字符串
          │  tokenize()            词法分析：切成 Token 序列
          ▼
      [Token, Token, ...]
          │  Parser.parse()        语法分析 + 求值（递归下降）
          ▼
      Decimal 结果
          │  format_decimal()     格式化：去掉多余的 0，避免科学计数法
          ▼
      结果字符串

3. 文法（EBNF）
       expression := term (('+' | '-') term)*
       term       := unary (('*' | '/') unary)*
       unary      := ('+' | '-') unary | primary
       primary    := NUMBER | '(' expression ')'

   该文法天然编码了运算符优先级：加减是表达式层，乘除是项层，
   越靠下的层结合越紧，因此 ``1 + 2 * 3`` 会被解析成 ``1 + (2 * 3)``。
   一元正负号放在 unary 层，所以 ``3 * -2`` 和 ``-5 + 8`` 都合法。

4. 为什么用 Decimal 而不是 float？
   float 是二进制浮点，``0.1 + 0.2`` 会得到 ``0.30000000000000004``。
   计算器出现这种结果体验很差。Decimal 是十进制运算，
   配合 28 位有效数字可以做到 ``0.1 + 0.2 == 0.3``，
   同时保留足够的精度余量。
"""

from __future__ import annotations

import re
from decimal import Decimal, DecimalException, InvalidOperation, localcontext
from enum import Enum

from src.core.config import settings
from src.core.exceptions import (
    DivisionByZeroError,
    ExpressionError,
    ExpressionTooLongError,
    ResultOverflowError,
)

# ============================================================
# 词法分析
# ============================================================


class TokenType(Enum):
    """Token 类型。"""

    NUMBER = "NUMBER"
    PLUS = "PLUS"
    MINUS = "MINUS"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


class Token:
    """词法单元：类型 + 原始文本 + 在字符串中的位置（用于精确报错）。"""

    __slots__ = ("type", "text", "position")

    def __init__(self, token_type: TokenType, text: str, position: int) -> None:
        self.type = token_type
        self.text = text
        self.position = position

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return f"Token({self.type.name}, {self.text!r}, pos={self.position})"


# 数字：整数或小数。允许 ".5" 与 "5." 两种写法，
# 但禁止 "1.2.3"（词法阶段会切出两个数字，语法阶段报错）。
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d*)?|\.\d+")

# 运算符字符 -> Token 类型
SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.MULTIPLY,
    "/": TokenType.DIVIDE,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
}

# 用户从界面复制过来的全角/易混字符，先统一归一化，提升容错性
NORMALIZE_MAP = str.maketrans(
    {
        "×": "*",
        "✕": "*",
        "✖": "*",
        "＊": "*",
        "÷": "/",
        "／": "/",
        "（": "(",
        "）": ")",
        "＋": "+",
        "－": "-",
        "−": "-",  # U+2212 数学减号
        "–": "-",  # en dash
        "—": "-",  # em dash
        "。": ".",
        "．": ".",
        "，": ",",
    }
)


def normalize_expression(raw: str) -> str:
    """归一化用户输入：统一全角符号、去掉全部空白字符。"""
    return raw.translate(NORMALIZE_MAP).replace(" ", "").replace("\t", "").replace("\n", "")


def tokenize(expression: str) -> list[Token]:
    """把表达式字符串切分为 Token 序列。

    Raises:
        ExpressionError: 遇到无法识别的字符。
    """
    tokens: list[Token] = []
    index = 0
    length = len(expression)

    while index < length:
        char = expression[index]

        # --- 数字 ---
        if char.isdigit() or char == ".":
            match = NUMBER_PATTERN.match(expression, index)
            if match is None:
                raise ExpressionError(
                    f"位置 {index + 1} 处的数字格式不正确：'{expression[index:]}'"
                )
            tokens.append(Token(TokenType.NUMBER, match.group(), index))
            index = match.end()
            continue

        # --- 运算符与括号 ---
        token_type = SINGLE_CHAR_TOKENS.get(char)
        if token_type is None:
            raise ExpressionError(
                f"表达式中包含非法字符 '{char}'（位置 {index + 1}）"
            )
        tokens.append(Token(token_type, char, index))
        index += 1

    tokens.append(Token(TokenType.EOF, "", length))
    return tokens


# ============================================================
# 语法分析 + 求值（递归下降）
# ============================================================


class Parser:
    """递归下降解析器，一边解析一边求值。

    之所以「边解析边求值」而不先建语法树：
    四则运算不需要复用中间结果，直接求值可以少一次遍历，
    代码也更短，便于在博客中讲清楚。
    """

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._cursor = 0

    # ---------- 游标辅助方法 ----------

    @property
    def _current(self) -> Token:
        return self._tokens[self._cursor]

    def _advance(self) -> Token:
        token = self._tokens[self._cursor]
        self._cursor += 1
        return token

    def _match(self, *token_types: TokenType) -> Token | None:
        """当前 Token 命中给定类型则消费并返回，否则返回 None。"""
        if self._current.type in token_types:
            return self._advance()
        return None

    # ---------- 文法规则 ----------

    def parse(self) -> Decimal:
        """入口：解析完整表达式并求值。"""
        value = self._parse_expression()
        if self._current.type is not TokenType.EOF:
            token = self._current
            raise ExpressionError(
                f"位置 {token.position + 1} 处存在多余的符号 '{token.text}'，"
                "请检查是否缺少运算符或括号"
            )
        return value

    def _parse_expression(self) -> Decimal:
        """expression := term (('+' | '-') term)*  —— 处理加减（优先级最低）。"""
        left = self._parse_term()

        while True:
            if self._match(TokenType.PLUS) is not None:
                left = left + self._parse_term()
            elif self._match(TokenType.MINUS) is not None:
                left = left - self._parse_term()
            else:
                return left

    def _parse_term(self) -> Decimal:
        """term := unary (('*' | '/') unary)*  —— 处理乘除（优先级高于加减）。"""
        left = self._parse_unary()

        while True:
            if self._match(TokenType.MULTIPLY) is not None:
                left = left * self._parse_unary()
            elif self._match(TokenType.DIVIDE) is not None:
                divisor = self._parse_unary()
                if divisor == 0:
                    # 显式拦截除以零，给出比 Decimal 原生异常更友好的提示
                    raise DivisionByZeroError("除数不能为零")
                left = left / divisor
            else:
                return left

    def _parse_unary(self) -> Decimal:
        """unary := ('+' | '-') unary | primary  —— 处理一元正负号。

        递归调用自身，因此 ``--5``、``-(-3)`` 也合法。
        """
        if self._match(TokenType.PLUS) is not None:
            return self._parse_unary()
        if self._match(TokenType.MINUS) is not None:
            return -self._parse_unary()
        return self._parse_primary()

    def _parse_primary(self) -> Decimal:
        """primary := NUMBER | '(' expression ')'  —— 数字与括号。"""
        token = self._current

        if token.type is TokenType.NUMBER:
            self._advance()
            try:
                return Decimal(token.text)
            except InvalidOperation as exc:  # pragma: no cover - 词法已保证
                raise ExpressionError(f"无法识别的数字 '{token.text}'") from exc

        if self._match(TokenType.LPAREN) is not None:
            value = self._parse_expression()
            if self._match(TokenType.RPAREN) is None:
                raise ExpressionError("括号不匹配：缺少右括号 ')'")
            return value

        if token.type is TokenType.RPAREN:
            raise ExpressionError(
                f"位置 {token.position + 1} 处出现多余的右括号 ')'"
            )

        if token.type is TokenType.EOF:
            raise ExpressionError("表达式不完整：末尾缺少数字或右括号")

        raise ExpressionError(
            f"位置 {token.position + 1} 处的运算符 '{token.text}' 使用不正确"
        )


# ============================================================
# 对外统一入口
# ============================================================


def validate_expression(raw: str) -> str:
    """校验并归一化表达式，返回可直接解析的字符串。

    做三重校验：非空 -> 长度上限 -> 字符集白名单。
    白名单是第一道防线，保证进入解析器的字符串只含数字和运算符。
    """
    if raw is None or not raw.strip():
        raise ExpressionError("表达式不能为空")

    normalized = normalize_expression(raw)

    if not normalized:
        raise ExpressionError("表达式不能为空")

    if len(normalized) > settings.max_expression_length:
        raise ExpressionTooLongError(
            f"表达式过长，最多支持 {settings.max_expression_length} 个字符"
        )

    illegal = set(normalized) - set("0123456789.+-*/()")
    if illegal:
        raise ExpressionError(
            "表达式包含非法字符：" + "、".join(sorted(illegal))
        )

    return normalized


def format_decimal(value: Decimal) -> str:
    """把 Decimal 格式化为对用户友好的字符串。

    处理三件事：
      1. 去掉末尾无意义的 0（``3.500`` -> ``3.5``）；
      2. 避免出现科学计数法（``1E+2`` -> ``100``）；
      3. 整数结果不带小数点（``6.0`` -> ``6``）。
    """
    if value == value.to_integral_value():
        # 整数：用 'f' 格式强制展开，避免 1E+2 这种写法
        return format(value.to_integral_value(), "f")

    # 先归一化去掉尾随零，再用定点格式输出
    normalized = value.normalize()
    sign, digits, exponent = normalized.as_tuple()

    # 位数过多时保留有效位，防止出现几百位小数的输出
    if isinstance(exponent, int) and exponent < -(settings.decimal_precision - 1):
        quantizer = Decimal(1).scaleb(exponent)
        normalized = normalized.quantize(quantizer) if quantizer else normalized

    text = format(normalized, "f")
    # 定点格式化可能残留尾随零，清理一次
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def evaluate(raw_expression: str) -> dict[str, object]:
    """计算入口：校验 -> 解析 -> 求值 -> 格式化。

    Args:
        raw_expression: 前端传来的原始表达式，例如 ``"(1+2)*3"``。

    Returns:
        形如 ``{"expression": "(1+2)*3", "normalized": "(1+2)*3", "result": "9"}``
        的字典，result 为字符串以保留原始精度。

    Raises:
        ExpressionError: 表达式非法。
        DivisionByZeroError: 除数为零。
        ResultOverflowError: 结果溢出。
    """
    normalized = validate_expression(raw_expression)
    tokens = tokenize(normalized)

    try:
        with localcontext() as ctx:
            # 提高精度余量，减少中间步骤的舍入误差
            ctx.prec = settings.decimal_precision
            value = Parser(tokens).parse()
    except DecimalException as exc:
        # Decimal 自身抛出的异常（溢出、无效运算等）统一转成业务异常
        raise ExpressionError("表达式计算失败，请检查数值是否合法") from exc

    if not value.is_finite():
        raise ResultOverflowError("计算结果超出可表示范围")

    if abs(value) > Decimal(settings.max_result_magnitude):
        raise ResultOverflowError(
            "计算结果过大，超出可表示范围，请缩小数值后重试"
        )

    return {
        "expression": raw_expression,
        "normalized": normalized,
        "result": format_decimal(value),
    }
