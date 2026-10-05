"""表达式引擎单元测试（对应作业功能一、功能二）。

覆盖：四则运算、运算优先级、括号、一元正负、小数精度、
非法表达式、除零、溢出、以及「禁止 eval」的安全边界。
"""

from __future__ import annotations

import unittest

from tests import ROOT  # noqa: F401  （导入即完成路径配置）
from src.core.exceptions import (
    DivisionByZeroError,
    ExpressionError,
    ExpressionTooLongError,
)
from src.service.calculator import evaluate, format_decimal, tokenize


class TestBasicCalculation(unittest.TestCase):
    """功能一：基础四则运算（15 分）。"""

    def test_addition(self) -> None:
        self.assertEqual(evaluate("12+8")["result"], "20")

    def test_subtraction(self) -> None:
        self.assertEqual(evaluate("12-8")["result"], "4")

    def test_multiplication(self) -> None:
        self.assertEqual(evaluate("12*8")["result"], "96")

    def test_division(self) -> None:
        self.assertEqual(evaluate("12/8")["result"], "1.5")

    def test_division_exact_integer(self) -> None:
        self.assertEqual(evaluate("100/4")["result"], "25")

    def test_all_four_operators(self) -> None:
        self.assertEqual(evaluate("1+2*3-4/2")["result"], "5")

    def test_negative_result(self) -> None:
        self.assertEqual(evaluate("3-10")["result"], "-7")


class TestOperatorPrecedence(unittest.TestCase):
    """功能二：运算优先级。"""

    def test_multiply_before_add(self) -> None:
        self.assertEqual(evaluate("1+2*3")["result"], "7")

    def test_division_before_subtraction(self) -> None:
        self.assertEqual(evaluate("10/2+7")["result"], "12")

    def test_mixed_precedence(self) -> None:
        self.assertEqual(evaluate("8-3*2")["result"], "2")

    def test_left_associativity(self) -> None:
        # 减法和除法必须左结合：(8-3)-2 = 3，而不是 8-(3-2) = 7
        self.assertEqual(evaluate("8-3-2")["result"], "3")
        self.assertEqual(evaluate("16/4/2")["result"], "2")


class TestParentheses(unittest.TestCase):
    """功能二：括号。"""

    def test_simple_parentheses(self) -> None:
        self.assertEqual(evaluate("(1+2)*3")["result"], "9")

    def test_nested_parentheses(self) -> None:
        self.assertEqual(evaluate("((1+2)*(3+4))")["result"], "21")

    def test_parentheses_override_precedence(self) -> None:
        self.assertEqual(evaluate("(8-3)*2")["result"], "10")

    def test_missing_right_parenthesis(self) -> None:
        with self.assertRaises(ExpressionError):
            evaluate("(1+2")

    def test_extra_right_parenthesis(self) -> None:
        with self.assertRaises(ExpressionError):
            evaluate("1+2)")


class TestUnaryOperator(unittest.TestCase):
    """功能二：一元正负号。"""

    def test_unary_minus_on_number(self) -> None:
        self.assertEqual(evaluate("-5+8")["result"], "3")

    def test_unary_minus_after_multiply(self) -> None:
        self.assertEqual(evaluate("3*-2")["result"], "-6")

    def test_unary_minus_in_parentheses(self) -> None:
        self.assertEqual(evaluate("(-3)*(4)")["result"], "-12")

    def test_unary_plus(self) -> None:
        self.assertEqual(evaluate("+7-2")["result"], "5")

    def test_double_negative(self) -> None:
        self.assertEqual(evaluate("--5")["result"], "5")

    def test_unary_minus_before_parenthesis(self) -> None:
        self.assertEqual(evaluate("-(2+3)")["result"], "-5")


class TestDecimal(unittest.TestCase):
    """功能二：小数运算（此处正是使用 Decimal 的价值所在）。"""

    def test_decimal_addition_is_exact(self) -> None:
        # 若用 float，这里会得到 0.30000000000000004
        self.assertEqual(evaluate("0.1+0.2")["result"], "0.3")

    def test_decimal_multiplication(self) -> None:
        self.assertEqual(evaluate("1.5*2")["result"], "3")

    def test_leading_dot(self) -> None:
        self.assertEqual(evaluate(".5+.5")["result"], "1")

    def test_trailing_dot(self) -> None:
        self.assertEqual(evaluate("3.*2")["result"], "6")

    def test_high_precision_keeps_reasonable_digits(self) -> None:
        result = evaluate("1/3")["result"]
        self.assertTrue(result.startswith("0.3333"))
        # 不应输出几百位小数
        self.assertLessEqual(len(result), 32)


class TestInvalidExpression(unittest.TestCase):
    """功能二：非法表达式处理。"""

    def test_empty_expression(self) -> None:
        with self.assertRaises(ExpressionError):
            evaluate("")

    def test_whitespace_only(self) -> None:
        with self.assertRaises(ExpressionError):
            evaluate("     ")

    def test_consecutive_operators(self) -> None:
        with self.assertRaises(ExpressionError):
            evaluate("1++*2")

    def test_trailing_operator(self) -> None:
        with self.assertRaises(ExpressionError):
            evaluate("1+")

    def test_illegal_characters(self) -> None:
        with self.assertRaises(ExpressionError):
            evaluate("1+a")

    def test_implicit_multiplication_is_rejected(self) -> None:
        # "2(3)" 是隐式乘法，本实现要求显式写出 * 号
        with self.assertRaises(ExpressionError):
            evaluate("2(3)")

    def test_number_after_number_is_rejected(self) -> None:
        with self.assertRaises(ExpressionError):
            evaluate("1.2.3")

    def test_whitespace_is_stripped_not_split(self) -> None:
        # 空白字符会被移除，因此 "1 2" 等价于 "12"（这是有意设计）
        self.assertEqual(evaluate("1 2")["result"], "12")

    def test_double_decimal_point(self) -> None:
        with self.assertRaises(ExpressionError):
            evaluate("1.2.3")

    def test_expression_too_long(self) -> None:
        with self.assertRaises(ExpressionTooLongError):
            evaluate("1+" * 200 + "1")


class TestDivisionByZero(unittest.TestCase):
    """功能二：除零处理。"""

    def test_simple_division_by_zero(self) -> None:
        with self.assertRaises(DivisionByZeroError):
            evaluate("1/0")

    def test_division_by_zero_expression(self) -> None:
        with self.assertRaises(DivisionByZeroError):
            evaluate("5/(3-3)")

    def test_division_by_zero_decimal(self) -> None:
        with self.assertRaises(DivisionByZeroError):
            evaluate("1/0.0")


class TestSecurity(unittest.TestCase):
    """安全边界：确认实现不依赖 eval，且恶意输入无法执行。"""

    def test_code_injection_is_rejected(self) -> None:
        payloads = [
            "__import__('os').system('whoami')",
            "1+open('/etc/passwd').read()",
            "eval('1+1')",
            "(lambda: 1)()",
            "1; import os",
            "[1,2,3]",
            "1 if True else 2",
            "9**9**9",
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ExpressionError):
                    evaluate(payload)

    def test_no_eval_in_source(self) -> None:
        """静态检查：核心模块中不得出现 eval / exec 调用。"""
        source = (ROOT / "src" / "service" / "calculator.py").read_text(
            encoding="utf-8"
        )
        code_lines = [
            line.split("#", 1)[0]
            for line in source.splitlines()
            if not line.strip().startswith(("#", '"', "'"))
        ]
        body = "\n".join(code_lines)
        self.assertNotIn("eval(", body)
        self.assertNotIn("exec(", body)

    def test_fullwidth_characters_are_normalized(self) -> None:
        # 用户从界面复制的 ×÷ 应被接受
        self.assertEqual(evaluate("6×7")["result"], "42")
        self.assertEqual(evaluate("8÷2")["result"], "4")
        self.assertEqual(evaluate("（1+2）*3")["result"], "9")


class TestTokenizerAndFormatter(unittest.TestCase):
    """词法分析与结果格式化。"""

    def test_tokenize_counts(self) -> None:
        tokens = tokenize("1+2")
        self.assertEqual(len(tokens), 4)  # NUMBER, PLUS, NUMBER, EOF

    def test_large_integer_has_no_scientific_notation(self) -> None:
        self.assertEqual(evaluate("100*100")["result"], "10000")

    def test_format_decimal_strips_trailing_zeros(self) -> None:
        from decimal import Decimal

        self.assertEqual(format_decimal(Decimal("3.500")), "3.5")
        self.assertEqual(format_decimal(Decimal("6.0")), "6")
        self.assertEqual(format_decimal(Decimal("1E+2")), "100")

    def test_negative_decimal(self) -> None:
        self.assertEqual(evaluate("-1.5*2")["result"], "-3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
