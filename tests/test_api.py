"""API 集成测试：用 FastAPI TestClient 走完整 HTTP 链路。

覆盖作业的四个必需功能在接口层的表现：
    功能一 基础计算     -> POST /api/calculate
    功能二 复合表达式   -> POST /api/calculate（含异常分支）
    功能三 计算历史     -> GET  /api/history（含持久化验证）
    功能四 删除历史     -> DELETE /api/history/{id}
"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from tests import ROOT  # noqa: F401  （导入即完成路径配置）
from src.core.database import get_connection, init_db
from src.main import app


class ApiTestCase(unittest.TestCase):
    """公共基类：每个测试前清空历史表，保证用例互不干扰。"""

    @classmethod
    def setUpClass(cls) -> None:
        init_db()
        cls.client = TestClient(app)

    def setUp(self) -> None:
        with get_connection() as connection:
            connection.execute("DELETE FROM calculation_history")

    # ---------- 便捷方法 ----------

    def calculate(self, expression: str, **extra):
        payload = {"expression": expression, **extra}
        return self.client.post("/api/calculate", json=payload)

    def assert_result(self, expression: str, expected: str) -> dict:
        response = self.calculate(expression)
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["result"], expected)
        return body


class TestHealthEndpoint(ApiTestCase):
    """健康检查（部署后用于确认服务存活）。"""

    def test_health_returns_ok(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["success"])
        self.assertIn("version", body)

    def test_root_endpoint(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["service"], "Calculator Backend")

    def test_openapi_document_available(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        for path in ("/api/calculate", "/api/history", "/api/health"):
            self.assertIn(path, paths)


class TestFeature1BasicCalculation(ApiTestCase):
    """功能一：基础计算（15 分）—— 结果必须由后端产生。"""

    def test_addition(self) -> None:
        self.assert_result("12+8", "20")

    def test_subtraction(self) -> None:
        self.assert_result("12-8", "4")

    def test_multiplication(self) -> None:
        self.assert_result("12*8", "96")

    def test_division(self) -> None:
        self.assert_result("12/8", "1.5")

    def test_frontend_symbols_are_accepted(self) -> None:
        """前端按钮发送的是 × ÷，后端应能直接处理。"""
        self.assert_result("6×7", "42")
        self.assert_result("8÷2", "4")

    def test_response_echoes_expression_and_record(self) -> None:
        body = self.assert_result("1+1", "2")
        self.assertEqual(body["expression"], "1+1")
        self.assertIn("record", body)
        self.assertIsInstance(body["record"]["id"], int)
        self.assertTrue(body["record"]["created_at"])

    def test_result_is_string_preserving_precision(self) -> None:
        body = self.assert_result("0.1+0.2", "0.3")
        self.assertIsInstance(body["result"], str)


class TestFeature2CompoundExpression(ApiTestCase):
    """功能二：复合表达式（15 分）。"""

    def test_operator_precedence(self) -> None:
        self.assert_result("1+2*3", "7")

    def test_parentheses(self) -> None:
        self.assert_result("(1+2)*3", "9")

    def test_division_and_addition(self) -> None:
        self.assert_result("10/2+7", "12")

    def test_subtraction_and_multiplication(self) -> None:
        self.assert_result("8-3*2", "2")

    def test_unary_minus(self) -> None:
        self.assert_result("-5+8", "3")

    def test_unary_minus_after_operator(self) -> None:
        self.assert_result("3*-2", "-6")

    def test_decimal_calculation(self) -> None:
        self.assert_result("1.5*2.5", "3.75")

    def test_nested_parentheses(self) -> None:
        self.assert_result("((2+3)*(4-1))/5", "3")

    def test_invalid_expression_returns_400(self) -> None:
        response = self.calculate("1++*2")
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "INVALID_EXPRESSION")

    def test_division_by_zero_returns_400_with_specific_code(self) -> None:
        response = self.calculate("1/0")
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["code"], "DIVISION_BY_ZERO")
        self.assertIn("零", body["message"])

    def test_invalid_expression_is_not_saved_to_history(self) -> None:
        """失败的表达式不应污染历史记录。"""
        self.calculate("1/0")
        self.calculate("abc")
        self.assertEqual(self.client.get("/api/history").json()["total"], 0)

    def test_missing_field_returns_422(self) -> None:
        response = self.client.post("/api/calculate", json={})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")

    def test_empty_expression_returns_422(self) -> None:
        response = self.calculate("")
        self.assertEqual(response.status_code, 422)

    def test_overlong_expression_is_rejected(self) -> None:
        response = self.calculate("1+" * 200 + "1")
        # 超过 Pydantic 的 max_length 时由校验层拦截
        self.assertIn(response.status_code, (400, 422))


class TestFeature3History(ApiTestCase):
    """功能三：计算历史（10 分）—— 必须落在数据库里。"""

    def test_calculation_is_persisted(self) -> None:
        self.calculate("1+2")
        response = self.client.get("/api/history")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        item = body["items"][0]
        self.assertEqual(item["expression"], "1+2")
        self.assertEqual(item["result"], "3")
        self.assertTrue(item["created_at"])

    def test_history_is_ordered_newest_first(self) -> None:
        for expression in ("1+1", "2+2", "3+3"):
            self.calculate(expression)
        items = self.client.get("/api/history").json()["items"]
        self.assertEqual([i["expression"] for i in items], ["3+3", "2+2", "1+1"])

    def test_history_survives_new_client_session(self) -> None:
        """模拟前端刷新/重启：新建 client 仍能读到数据。"""
        self.calculate("7*6")
        with TestClient(app) as fresh_client:
            body = fresh_client.get("/api/history").json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["result"], "42")

    def test_data_is_really_in_database(self) -> None:
        """绕过 API，直接查库确认数据确实落盘。"""
        self.calculate("9+9")
        with get_connection() as connection:
            row = connection.execute(
                "SELECT expression, result FROM calculation_history"
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["expression"], "9+9")
        self.assertEqual(row["result"], "18")

    def test_pagination(self) -> None:
        for index in range(25):
            self.calculate(f"{index}+1")
        body = self.client.get("/api/history?page=1&page_size=10").json()
        self.assertEqual(len(body["items"]), 10)
        self.assertEqual(body["total"], 25)
        self.assertEqual(body["total_pages"], 3)

    def test_keyword_search(self) -> None:
        self.calculate("123+1")
        self.calculate("5+5")
        body = self.client.get("/api/history?keyword=123").json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["expression"], "123+1")

    def test_get_single_record(self) -> None:
        record_id = self.calculate("4+4").json()["record"]["id"]
        response = self.client.get(f"/api/history/{record_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "8")

    def test_get_missing_record_returns_404(self) -> None:
        response = self.client.get("/api/history/999999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "RECORD_NOT_FOUND")


class TestFeature4DeleteHistory(ApiTestCase):
    """功能四：删除历史（10 分）—— 必须真的从库里删掉。"""

    def test_delete_specified_record(self) -> None:
        first = self.calculate("1+1").json()["record"]["id"]
        second = self.calculate("2+2").json()["record"]["id"]

        response = self.client.delete(f"/api/history/{first}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted_id"], first)

        remaining = self.client.get("/api/history").json()
        self.assertEqual(remaining["total"], 1)
        self.assertEqual(remaining["items"][0]["id"], second)

    def test_delete_removes_row_from_database(self) -> None:
        record_id = self.calculate("3+3").json()["record"]["id"]
        self.client.delete(f"/api/history/{record_id}")
        with get_connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM calculation_history WHERE id = ?", (record_id,)
            ).fetchone()
        self.assertIsNone(row)

    def test_delete_missing_record_returns_404(self) -> None:
        response = self.client.delete("/api/history/999999")
        self.assertEqual(response.status_code, 404)

    def test_clear_all_history(self) -> None:
        for index in range(4):
            self.calculate(f"{index}+1")
        response = self.client.delete("/api/history")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deleted_count"], 4)
        self.assertEqual(self.client.get("/api/history").json()["total"], 0)


class TestExtendedFeatures(ApiTestCase):
    """扩展功能对应的接口。"""

    def test_toggle_favorite(self) -> None:
        record_id = self.calculate("5+5").json()["record"]["id"]
        response = self.client.patch(f"/api/history/{record_id}/favorite")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["record"]["is_favorite"])

        # 再切一次应回到未收藏
        response = self.client.patch(f"/api/history/{record_id}/favorite")
        self.assertFalse(response.json()["record"]["is_favorite"])

    def test_favorites_filter(self) -> None:
        favorite_id = self.calculate("1+0").json()["record"]["id"]
        self.calculate("2+0")
        self.client.patch(f"/api/history/{favorite_id}/favorite")

        body = self.client.get("/api/history?favorites_only=true").json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["id"], favorite_id)

    def test_statistics(self) -> None:
        self.calculate("1+1")
        self.calculate("2+2")
        body = self.client.get("/api/statistics").json()
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["favorites"], 0)
        self.assertEqual(body["today"], 2)
        self.assertTrue(body["latest_at"])

    def test_extended_flag_is_recorded(self) -> None:
        body = self.calculate("2*3", is_extended=True).json()
        self.assertTrue(body["record"]["is_extended"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
