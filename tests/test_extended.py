"""扩展功能测试：科学计算 / 进制转换 / 单位换算（加分项）。"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from tests import ROOT  # noqa: F401  （导入即完成路径配置）
from src.core.database import get_connection, init_db
from src.main import app


class ExtendedApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_db()
        cls.client = TestClient(app)

    def setUp(self) -> None:
        with get_connection() as connection:
            connection.execute("DELETE FROM calculation_history")

    def post_extended(self, payload: dict):
        return self.client.post("/api/extended", json=payload)


class TestScientificCalculation(ExtendedApiTestCase):
    """科学计算。"""

    def test_square_root(self) -> None:
        response = self.post_extended(
            {"type": "scientific", "function": "sqrt", "operands": ["16"]}
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["result"], "4")

    def test_power_with_two_operands(self) -> None:
        response = self.post_extended(
            {"type": "scientific", "function": "power", "operands": ["2", "10"]}
        )
        self.assertEqual(response.json()["result"], "1024")

    def test_factorial(self) -> None:
        response = self.post_extended(
            {"type": "scientific", "function": "factorial", "operands": ["5"]}
        )
        self.assertEqual(response.json()["result"], "120")

    def test_trigonometric_uses_degrees(self) -> None:
        response = self.post_extended(
            {"type": "scientific", "function": "sin", "operands": ["30"]}
        )
        self.assertEqual(response.json()["result"], "0.5")

    def test_sqrt_of_negative_is_rejected(self) -> None:
        response = self.post_extended(
            {"type": "scientific", "function": "sqrt", "operands": ["-4"]}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_EXPRESSION")

    def test_log_of_zero_is_rejected(self) -> None:
        response = self.post_extended(
            {"type": "scientific", "function": "log10", "operands": ["0"]}
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_function_is_rejected(self) -> None:
        response = self.post_extended(
            {"type": "scientific", "function": "os_system", "operands": ["1"]}
        )
        self.assertEqual(response.status_code, 400)

    def test_wrong_operand_count_is_rejected(self) -> None:
        response = self.post_extended(
            {"type": "scientific", "function": "sqrt", "operands": ["1", "2"]}
        )
        self.assertEqual(response.status_code, 400)

    def test_result_is_saved_to_history_as_extended(self) -> None:
        self.post_extended(
            {"type": "scientific", "function": "sqrt", "operands": ["81"]}
        )
        body = self.client.get("/api/history").json()
        self.assertEqual(body["total"], 1)
        self.assertTrue(body["items"][0]["is_extended"])

    def test_capabilities_endpoint(self) -> None:
        response = self.client.get("/api/extended/capabilities")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreaterEqual(len(body["scientific_functions"]), 10)
        self.assertEqual(len(body["unit_categories"]), 4)


class TestBaseConversion(ExtendedApiTestCase):
    """进制转换。"""

    def test_decimal_to_binary(self) -> None:
        response = self.post_extended(
            {"type": "base", "value": "255", "from_base": 10, "to_base": 2}
        )
        self.assertEqual(response.json()["result"], "11111111")

    def test_decimal_to_hex_is_uppercase(self) -> None:
        response = self.post_extended(
            {"type": "base", "value": "255", "from_base": 10, "to_base": 16}
        )
        self.assertEqual(response.json()["result"], "FF")

    def test_binary_to_decimal(self) -> None:
        response = self.post_extended(
            {"type": "base", "value": "1010", "from_base": 2, "to_base": 10}
        )
        self.assertEqual(response.json()["result"], "10")

    def test_hex_with_prefix_accepted(self) -> None:
        response = self.post_extended(
            {"type": "base", "value": "0xFF", "from_base": 16, "to_base": 10}
        )
        self.assertEqual(response.json()["result"], "255")

    def test_invalid_digit_for_base_is_rejected(self) -> None:
        response = self.post_extended(
            {"type": "base", "value": "129", "from_base": 8, "to_base": 10}
        )
        self.assertEqual(response.status_code, 400)

    def test_unsupported_base_is_rejected(self) -> None:
        response = self.post_extended(
            {"type": "base", "value": "10", "from_base": 3, "to_base": 10}
        )
        self.assertEqual(response.status_code, 400)

    def test_hex_output_is_uppercase(self) -> None:
        """十六进制结果必须大写，这是常见的展示规范。"""
        response = self.post_extended(
            {"type": "base", "value": "255", "from_base": 10, "to_base": 16}
        )
        self.assertEqual(response.json()["result"], "FF")

    def test_display_echoes_user_input_without_altering_case(self) -> None:
        """回显必须原样保留用户输入的大小写。

        早期实现把输入整体 lower() 后用于回显，导致用户输入 "FF"
        却显示成 "ff"。这个断言专门防止该类回显缺陷回归。
        """
        response = self.post_extended(
            {"type": "base", "value": "FF", "from_base": 16, "to_base": 10}
        )
        body = response.json()
        self.assertEqual(body["result"], "255")
        self.assertIn("FF", body["display"])
        self.assertNotIn("ff", body["display"])

    def test_binary_result_is_not_mangled_by_prefix_stripping(self) -> None:
        """二进制结果中本身含 "0b" 时不能被误删。

        早期实现用 replace("0b", "") 去前缀，会把数值 11（二进制 1011，
        其十进制表示含 0b 子串的场景）等数据破坏。这里用 0b0b1 这类
        输入验证结果保持正确。
        """
        # 十进制 11 -> 二进制 "1011"
        response = self.post_extended(
            {"type": "base", "value": "11", "from_base": 10, "to_base": 2}
        )
        self.assertEqual(response.json()["result"], "1011")

        # 十进制 283 -> 二进制 "100011011"，含 "0b" 相邻字符的字面量
        response = self.post_extended(
            {"type": "base", "value": "283", "from_base": 10, "to_base": 2}
        )
        self.assertEqual(response.json()["result"], "100011011")

    def test_all_four_bases_round_trip(self) -> None:
        """同一个数值在四种进制之间往返转换应保持一致。"""
        for to_base, expected in ((2, "11111111"), (8, "377"), (10, "255"), (16, "FF")):
            with self.subTest(to_base=to_base):
                response = self.post_extended(
                    {"type": "base", "value": "255", "from_base": 10, "to_base": to_base}
                )
                self.assertEqual(response.json()["result"], expected)

                # 再转回十进制应还原为 255
                back = self.post_extended(
                    {"type": "base", "value": expected, "from_base": to_base, "to_base": 10}
                )
                self.assertEqual(back.json()["result"], "255")


class TestUnitConversion(ExtendedApiTestCase):
    """单位换算。"""

    def test_km_to_m(self) -> None:
        response = self.post_extended(
            {
                "type": "unit",
                "category": "length",
                "value": "1.5",
                "from_unit": "km",
                "to_unit": "m",
            }
        )
        self.assertEqual(response.json()["result"], "1500")

    def test_inch_to_cm(self) -> None:
        response = self.post_extended(
            {
                "type": "unit",
                "category": "length",
                "value": "1",
                "from_unit": "inch",
                "to_unit": "cm",
            }
        )
        self.assertEqual(response.json()["result"], "2.54")

    def test_kg_to_pound(self) -> None:
        response = self.post_extended(
            {
                "type": "unit",
                "category": "mass",
                "value": "1",
                "from_unit": "kg",
                "to_unit": "pound",
            }
        )
        self.assertAlmostEqual(float(response.json()["result"]), 2.20462262, places=6)

    def test_celsius_to_fahrenheit(self) -> None:
        response = self.post_extended(
            {
                "type": "unit",
                "category": "temperature",
                "value": "100",
                "from_unit": "c",
                "to_unit": "f",
            }
        )
        self.assertEqual(response.json()["result"], "212")

    def test_fahrenheit_to_celsius(self) -> None:
        response = self.post_extended(
            {
                "type": "unit",
                "category": "temperature",
                "value": "32",
                "from_unit": "f",
                "to_unit": "c",
            }
        )
        self.assertEqual(response.json()["result"], "0")

    def test_kelvin_to_celsius(self) -> None:
        response = self.post_extended(
            {
                "type": "unit",
                "category": "temperature",
                "value": "273.15",
                "from_unit": "k",
                "to_unit": "c",
            }
        )
        self.assertEqual(response.json()["result"], "0")

    def test_invalid_unit_is_rejected(self) -> None:
        response = self.post_extended(
            {
                "type": "unit",
                "category": "length",
                "value": "1",
                "from_unit": "lightyear",
                "to_unit": "m",
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_number_is_rejected(self) -> None:
        response = self.post_extended(
            {
                "type": "unit",
                "category": "length",
                "value": "abc",
                "from_unit": "m",
                "to_unit": "km",
            }
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
