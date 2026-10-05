"""业务层：扩展功能计算（科学计算、进制转换、单位换算）。

设计说明：
    基础四则运算走 calculator.py 的表达式引擎；
    本模块处理「一元函数」和「格式转换」这类不属于中缀表达式的运算。

    所有运算同样在后端完成，前端只负责传参和展示，
    因此扩展功能也满足「核心计算必须由后端完成」的要求。

    扩展功能只是加分项，本模块的实现刻意保持简单，
    不引入 math 之外的科学计算库，避免增加部署复杂度。
"""

from __future__ import annotations

import math
from decimal import Decimal, DecimalException, localcontext
from typing import Any

from src.core.config import settings
from src.core.exceptions import ExpressionError

# ---------------------------------------------------------------
# 科学计算：函数名 -> (所需参数个数, 实现函数)
# 只接受白名单内的函数名，杜绝通过函数名注入任意调用。
# ---------------------------------------------------------------


def _to_float(value: str) -> float:
    """把前端传来的数字字符串转成 float，失败则抛业务异常。"""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ExpressionError(f"'{value}' 不是合法的数字") from exc
    if math.isnan(number) or math.isinf(number):
        raise ExpressionError(f"数字 '{value}' 超出可计算范围")
    return number


def _sqrt(value: str) -> float:
    number = _to_float(value)
    if number < 0:
        raise ExpressionError("负数不能开平方（本计算器暂不支持复数）")
    return math.sqrt(number)


def _log10(value: str) -> float:
    number = _to_float(value)
    if number <= 0:
        raise ExpressionError("对数的真数必须大于 0")
    return math.log10(number)


def _ln(value: str) -> float:
    number = _to_float(value)
    if number <= 0:
        raise ExpressionError("对数的真数必须大于 0")
    return math.log(number)


def _factorial(value: str) -> int:
    number = _to_float(value)
    if number < 0 or not number.is_integer():
        raise ExpressionError("阶乘只支持非负整数")
    if number > 170:
        # 170! 已接近 float 上限，继续算下去会溢出
        raise ExpressionError("阶乘参数过大（最大支持 170）")
    return math.factorial(int(number))


def _log2(value: str) -> float:
    number = _to_float(value)
    if number <= 0:
        raise ExpressionError("对数的真数必须大于 0")
    return math.log2(number)


def _reciprocal(value: str) -> float:
    number = _to_float(value)
    if number == 0:
        raise ExpressionError("0 没有倒数")
    return 1 / number


SCIENTIFIC_FUNCTIONS: dict[str, tuple[int, Any]] = {
    "sqrt": (1, _sqrt),
    "square": (1, lambda v: _to_float(v) ** 2),
    "cube": (1, lambda v: _to_float(v) ** 3),
    "power": (2, lambda a, b: _to_float(a) ** _to_float(b)),
    "reciprocal": (1, _reciprocal),
    "abs": (1, lambda v: abs(_to_float(v))),
    "log10": (1, _log10),
    "ln": (1, _ln),
    "log2": (1, _log2),
    "exp": (1, lambda v: math.exp(_to_float(v))),
    "factorial": (1, _factorial),
    "sin": (1, lambda v: math.sin(math.radians(_to_float(v)))),  # 按角度制
    "cos": (1, lambda v: math.cos(math.radians(_to_float(v)))),
    "tan": (1, lambda v: math.tan(math.radians(_to_float(v)))),
    "ceil": (1, lambda v: math.ceil(_to_float(v))),
    "floor": (1, lambda v: math.floor(_to_float(v))),
    "round": (1, lambda v: round(_to_float(v))),
}

# 面向用户的中文函数说明，前端展示用
FUNCTION_LABELS: dict[str, str] = {
    "sqrt": "平方根",
    "square": "平方",
    "cube": "立方",
    "power": "幂运算 a^b",
    "reciprocal": "倒数",
    "abs": "绝对值",
    "log10": "常用对数",
    "ln": "自然对数",
    "log2": "以 2 为底对数",
    "exp": "e 的幂",
    "factorial": "阶乘",
    "sin": "正弦（角度）",
    "cos": "余弦（角度）",
    "tan": "正切（角度）",
    "ceil": "向上取整",
    "floor": "向下取整",
    "round": "四舍五入",
}


def _format_number(value: float | int) -> str:
    """把计算结果格式化成干净的数字字符串。"""
    if isinstance(value, int):
        return str(value)
    if math.isnan(value) or math.isinf(value):
        raise ExpressionError("计算结果超出可表示范围")
    if value.is_integer() and abs(value) < 1e16:
        return str(int(value))
    # 用 repr 获得最短往返表示，再清理多余的尾随零
    text = repr(round(value, 12))
    if "e" in text or "E" in text:
        return text
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def calculate_scientific(function: str, operands: list[str]) -> dict[str, Any]:
    """执行一元/二元科学计算。

    Args:
        function: 函数名，必须在 SCIENTIFIC_FUNCTIONS 白名单内。
        operands: 操作数列表（字符串形式）。

    Returns:
        ``{"function": ..., "operands": ..., "result": ..., "display": ...}``
    """
    handler = SCIENTIFIC_FUNCTIONS.get(function)
    if handler is None:
        raise ExpressionError(
            f"不支持的函数 '{function}'，可用函数："
            + ", ".join(sorted(SCIENTIFIC_FUNCTIONS))
        )

    arity, implementation = handler
    if len(operands) != arity:
        raise ExpressionError(
            f"函数 '{function}' 需要 {arity} 个参数，实际收到 {len(operands)} 个"
        )

    try:
        raw = implementation(*operands)
    except ExpressionError:
        raise
    except ZeroDivisionError as exc:
        raise ExpressionError("除数不能为零") from exc
    except (ValueError, OverflowError, DecimalException) as exc:
        raise ExpressionError(f"计算失败：{exc}") from exc

    result = _format_number(raw)
    label = FUNCTION_LABELS.get(function, function)
    display = f"{label}({', '.join(operands)}) = {result}"

    # 同时生成一个可用于写入历史记录的「表达式」文本
    expression = f"{function}({','.join(operands)})"

    return {
        "function": function,
        "operands": operands,
        "result": result,
        "display": display,
        "expression": expression,
    }


# ---------------------------------------------------------------
# 进制转换
# ---------------------------------------------------------------

BASE_NAMES: dict[int, str] = {2: "二进制", 8: "八进制", 10: "十进制", 16: "十六进制"}
SUPPORTED_BASES = tuple(BASE_NAMES)


def convert_base(value: str, from_base: int, to_base: int) -> dict[str, Any]:
    """在不同进制之间转换数值。

    只支持非负整数，避免小数与负数带来的歧义（作业扩展项，够用即可）。
    """
    if from_base not in BASE_NAMES:
        raise ExpressionError(f"不支持的源进制 {from_base}，仅支持 2/8/10/16")
    if to_base not in BASE_NAMES:
        raise ExpressionError(f"不支持的目标进制 {to_base}，仅支持 2/8/10/16")

    # 保留用户原始输入用于回显（如输入 "FF" 就显示 "FF"，不擅自改成小写）；
    # 解析时再统一去掉空白与小写化，因为 int() 本身不区分大小写。
    raw_text = (value or "").strip()
    normalized = raw_text.lower().replace(" ", "")
    if not normalized:
        raise ExpressionError("请输入要转换的数值")

    try:
        number = int(normalized, from_base)
    except ValueError as exc:
        raise ExpressionError(
            f"'{raw_text}' 不是合法的{BASE_NAMES[from_base]}数"
        ) from exc

    if number < 0:
        raise ExpressionError("进制转换暂不支持负数")

    # 格式化输出：十六进制统一大写；二/八/十进制直接用对应函数
    if to_base == 16:
        converted = format(number, "X")
    elif to_base == 2:
        converted = format(number, "b")
    elif to_base == 8:
        converted = format(number, "o")
    else:
        converted = str(number)

    return {
        "value": raw_text,
        "from_base": from_base,
        "to_base": to_base,
        "result": converted,
        "display": (
            f"{BASE_NAMES[from_base]} {raw_text} = "
            f"{BASE_NAMES[to_base]} {converted}"
        ),
        "expression": f"convert({raw_text},{from_base}->{to_base})",
    }


# ---------------------------------------------------------------
# 单位换算
# ---------------------------------------------------------------

# 每个类别：单位名 -> 相对基准单位的系数
UNIT_CATEGORIES: dict[str, dict[str, Decimal]] = {
    "length": {  # 基准：米
        "mm": Decimal("0.001"),
        "cm": Decimal("0.01"),
        "m": Decimal("1"),
        "km": Decimal("1000"),
        "inch": Decimal("0.0254"),
        "foot": Decimal("0.3048"),
        "mile": Decimal("1609.344"),
    },
    "mass": {  # 基准：千克
        "mg": Decimal("0.000001"),
        "g": Decimal("0.001"),
        "kg": Decimal("1"),
        "ton": Decimal("1000"),
        "pound": Decimal("0.45359237"),
        "ounce": Decimal("0.028349523125"),
    },
    "area": {  # 基准：平方米
        "cm2": Decimal("0.0001"),
        "m2": Decimal("1"),
        "km2": Decimal("1000000"),
        "hectare": Decimal("10000"),
        "mu": Decimal("666.6666666666666666666666667"),  # 亩
    },
    "temperature": {},  # 温度需要偏移量，单独处理
}

UNIT_LABELS: dict[str, dict[str, str]] = {
    "length": {
        "mm": "毫米",
        "cm": "厘米",
        "m": "米",
        "km": "千米",
        "inch": "英寸",
        "foot": "英尺",
        "mile": "英里",
    },
    "mass": {
        "mg": "毫克",
        "g": "克",
        "kg": "千克",
        "ton": "吨",
        "pound": "磅",
        "ounce": "盎司",
    },
    "area": {
        "cm2": "平方厘米",
        "m2": "平方米",
        "km2": "平方千米",
        "hectare": "公顷",
        "mu": "亩",
    },
    "temperature": {"c": "摄氏度", "f": "华氏度", "k": "开尔文"},
}

CATEGORY_LABELS: dict[str, str] = {
    "length": "长度",
    "mass": "质量",
    "area": "面积",
    "temperature": "温度",
}


def _temperature_to_celsius(value: Decimal, unit: str) -> Decimal:
    if unit == "c":
        return value
    if unit == "f":
        return (value - Decimal("32")) * Decimal("5") / Decimal("9")
    if unit == "k":
        return value - Decimal("273.15")
    raise ExpressionError(f"不支持的温度单位 '{unit}'")


def _celsius_to_temperature(value: Decimal, unit: str) -> Decimal:
    if unit == "c":
        return value
    if unit == "f":
        return value * Decimal("9") / Decimal("5") + Decimal("32")
    if unit == "k":
        return value + Decimal("273.15")
    raise ExpressionError(f"不支持的温度单位 '{unit}'")


def convert_unit(
    category: str, value: str, from_unit: str, to_unit: str
) -> dict[str, Any]:
    """单位换算：长度 / 质量 / 面积 / 温度。"""
    if category not in UNIT_CATEGORIES:
        raise ExpressionError(
            f"不支持的单位类别 '{category}'，可用："
            + ", ".join(UNIT_CATEGORIES)
        )

    valid_units = UNIT_LABELS[category]
    if from_unit not in valid_units:
        raise ExpressionError(f"'{from_unit}' 不是合法的{UNIT_LABELS[category]}单位")
    if to_unit not in valid_units:
        raise ExpressionError(f"'{to_unit}' 不是合法的{UNIT_LABELS[category]}单位")

    try:
        number = Decimal((value or "").strip())
    except (DecimalException, ArithmeticError) as exc:
        raise ExpressionError(f"'{value}' 不是合法的数字") from exc

    with localcontext() as ctx:
        ctx.prec = settings.decimal_precision
        if category == "temperature":
            celsius = _temperature_to_celsius(number, from_unit)
            converted = _celsius_to_temperature(celsius, to_unit)
        else:
            factors = UNIT_CATEGORIES[category]
            converted = number * factors[from_unit] / factors[to_unit]

    result = _format_decimal_for_display(converted)
    from_label = valid_units[from_unit]
    to_label = valid_units[to_unit]

    return {
        "category": category,
        "value": str(number),
        "from_unit": from_unit,
        "to_unit": to_unit,
        "result": result,
        "display": f"{number} {from_label} = {result} {to_label}",
        "expression": f"unit({number}{from_unit}->{to_unit})",
    }


def _format_decimal_for_display(value: Decimal) -> str:
    """单位换算结果格式化：保留合理位数，去掉多余的零。"""
    if value == value.to_integral_value():
        return format(value.to_integral_value(), "f")
    quantized = value.quantize(Decimal("0.0000000001"))
    text = format(quantized, "f").rstrip("0").rstrip(".")
    return text or "0"
