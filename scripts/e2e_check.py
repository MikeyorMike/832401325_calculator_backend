"""端到端验证脚本：通过真实 HTTP 请求走完整业务链路。

与 tests/ 下的单元测试不同，本脚本不依赖 TestClient，
而是对「已经启动的服务进程」发起真实网络请求，
用于验证部署后的实际行为（含 CORS、路由、静态挂载等）。

用法：
    python scripts/e2e_check.py [base_url]
默认 base_url 为 http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")

PASSED = 0
FAILED: list[str] = []


def request(
    method: str,
    path: str,
    payload: dict | None = None,
    origin: str | None = None,
    preflight_method: str | None = None,
    parse_json: bool = True,
):
    """发起 HTTP 请求，返回 (状态码, 响应体, 响应头)。

    Args:
        preflight_method: 设置该值会附加 CORS 预检所需的
            Access-Control-Request-Method 头；浏览器发预检请求时一定会带它。
        parse_json: 响应不是 JSON（例如 /docs 返回 HTML）时置为 False。
    """
    url = BASE_URL + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if origin:
        headers["Origin"] = origin
    if preflight_method:
        headers["Access-Control-Request-Method"] = preflight_method
        headers["Access-Control-Request-Headers"] = "content-type"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
            body = None
            if raw and parse_json:
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    body = {"raw_length": len(raw)}
            return response.status, body, dict(response.headers)
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw and parse_json else None
        except json.JSONDecodeError:
            body = {"raw_length": len(raw)}
        return error.code, body, dict(error.headers)


def check(label: str, condition: bool, extra: str = "") -> None:
    """记录一条断言结果。"""
    global PASSED
    if condition:
        PASSED += 1
        print(f"  [PASS] {label}")
    else:
        FAILED.append(label)
        print(f"  [FAIL] {label} {extra}")


def main() -> int:
    print(f"端到端验证目标：{BASE_URL}\n")

    # ---------- 1. 健康检查 ----------
    print("1) 健康检查")
    status, body, _ = request("GET", "/api/health")
    check("GET /api/health 返回 200", status == 200, f"实际 {status}")
    check("状态为 ok", bool(body) and body.get("status") == "ok")

    # ---------- 2. 基础计算（功能一） ----------
    print("\n2) 功能一：基础四则运算")
    cases = [("12+8", "20"), ("12-8", "4"), ("12*8", "96"), ("12/8", "1.5")]
    for expression, expected in cases:
        status, body, _ = request("POST", "/api/calculate", {"expression": expression})
        actual = body.get("result") if body else None
        check(f"{expression} = {expected}", status == 201 and actual == expected,
              f"实际 {status} / {actual}")

    # 前端按钮使用的 × ÷ 符号
    status, body, _ = request("POST", "/api/calculate", {"expression": "6×7"})
    check("前端符号 6×7 = 42", status == 201 and body.get("result") == "42")

    # ---------- 3. 复合表达式（功能二） ----------
    print("\n3) 功能二：复合表达式")
    compound = [
        ("1+2*3", "7"), ("(1+2)*3", "9"), ("10/2+7", "12"),
        ("8-3*2", "2"), ("-5+8", "3"), ("3*-2", "-6"),
        ("0.1+0.2", "0.3"), ("((2+3)*(4-1))/5", "3"),
    ]
    for expression, expected in compound:
        status, body, _ = request("POST", "/api/calculate", {"expression": expression})
        actual = body.get("result") if body else None
        check(f"{expression} = {expected}", status == 201 and actual == expected,
              f"实际 {status} / {actual}")

    print("\n4) 功能二：异常处理")
    status, body, _ = request("POST", "/api/calculate", {"expression": "1/0"})
    check("除零返回 400", status == 400, f"实际 {status}")
    check("除零错误码正确", bool(body) and body.get("code") == "DIVISION_BY_ZERO")

    status, body, _ = request("POST", "/api/calculate", {"expression": "1++*2"})
    check("非法表达式返回 400", status == 400, f"实际 {status}")
    check("非法表达式错误码正确", bool(body) and body.get("code") == "INVALID_EXPRESSION")

    status, body, _ = request("POST", "/api/calculate",
                              {"expression": "__import__('os').system('whoami')"})
    check("代码注入被拒绝", status == 400, f"实际 {status}")

    # ---------- 5. 计算历史（功能三） ----------
    print("\n5) 功能三：计算历史")
    status, body, _ = request("GET", "/api/history?page=1&page_size=5")
    check("分页查询返回 200", status == 200, f"实际 {status}")
    check("返回结构包含分页字段",
          bool(body) and {"items", "total", "page", "total_pages"} <= set(body.keys()))
    total_before = body.get("total") if body else 0
    check("历史已有记录", total_before > 0, f"total={total_before}")

    first_item = body["items"][0] if body and body["items"] else {}
    check("记录含表达式/结果/时间三要素",
          {"expression", "result", "created_at"} <= set(first_item.keys()))

    # 关键字搜索
    status, body, _ = request("GET", "/api/history?keyword=12%2B8")
    check("关键字搜索可用", status == 200 and bool(body) and body.get("total", 0) >= 1)

    # ---------- 6. 删除历史（功能四） ----------
    print("\n6) 功能四：删除指定历史记录")
    status, body, _ = request("POST", "/api/calculate", {"expression": "777+1"})
    record_id = body["record"]["id"]
    check("新增记录成功", status == 201 and body["result"] == "778")

    status, body, _ = request("DELETE", f"/api/history/{record_id}")
    check("删除返回 200", status == 200, f"实际 {status}")
    check("删除响应含 deleted_id", bool(body) and body.get("deleted_id") == record_id)

    status, _, _ = request("GET", f"/api/history/{record_id}")
    check("删除后查询该记录返回 404", status == 404, f"实际 {status}")

    status, _, _ = request("DELETE", "/api/history/999999")
    check("删除不存在的记录返回 404", status == 404, f"实际 {status}")

    # ---------- 7. 扩展功能 ----------
    print("\n7) 扩展功能")
    status, body, _ = request("POST", "/api/extended",
                              {"type": "scientific", "function": "sqrt", "operands": ["144"]})
    check("科学计算 √144 = 12", status == 201 and body.get("result") == "12",
          f"实际 {status} / {body.get('result') if body else None}")

    status, body, _ = request("POST", "/api/extended",
                              {"type": "base", "value": "255", "from_base": 10, "to_base": 2})
    check("进制转换 255 -> 11111111",
          status == 201 and body.get("result") == "11111111")

    status, body, _ = request("POST", "/api/extended",
                              {"type": "unit", "category": "temperature", "value": "100",
                               "from_unit": "c", "to_unit": "f"})
    check("单位换算 100°C = 212°F", status == 201 and body.get("result") == "212")

    status, body, _ = request("GET", "/api/extended/capabilities")
    check("能力清单返回 200", status == 200 and bool(body) and
          len(body.get("scientific_functions", [])) >= 10)

    status, body, _ = request("GET", "/api/statistics")
    check("统计接口返回 200", status == 200 and bool(body) and "total" in body)

    # ---------- 8. 收藏 ----------
    print("\n8) 收藏与筛选")
    status, body, _ = request("POST", "/api/calculate", {"expression": "1+2"})
    fav_id = body["record"]["id"]
    status, body, _ = request("PATCH", f"/api/history/{fav_id}/favorite")
    check("切换收藏成功", status == 200 and body["record"]["is_favorite"] is True)
    status, body, _ = request("GET", "/api/history?favorites_only=true")
    check("仅看收藏筛选可用", status == 200 and body.get("total", 0) >= 1)

    # ---------- 9. CORS ----------
    print("\n9) 跨域（前后端分离部署的关键）")
    status, _, headers = request("GET", "/api/health", origin="https://example.netlify.app")
    allow_origin = headers.get("access-control-allow-origin")
    check("响应包含 CORS 头", allow_origin is not None, f"headers={allow_origin}")
    check("CORS 允许该来源", allow_origin in ("*", "https://example.netlify.app"),
          f"实际 {allow_origin}")

    status, _, headers = request(
        "OPTIONS",
        "/api/calculate",
        origin="https://example.netlify.app",
        preflight_method="POST",
    )
    check("预检请求 OPTIONS 被接受", status in (200, 204), f"实际 {status}")
    check(
        "预检响应允许 POST",
        headers.get("access-control-allow-methods", "").upper().find("POST") >= 0,
        f"实际 {headers.get('access-control-allow-methods')}",
    )

    # ---------- 10. 文档 ----------
    print("\n10) 接口文档")
    status, _, _ = request("GET", "/docs", parse_json=False)
    check("Swagger UI 可访问", status == 200, f"实际 {status}")
    status, body, _ = request("GET", "/openapi.json")
    check("OpenAPI 描述可访问", status == 200 and bool(body))
    paths = set(body["paths"].keys()) if body else set()
    check("接口文档包含四个必需端点",
          {"/api/calculate", "/api/history", "/api/history/{record_id}"} <= paths)

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print(f"通过 {PASSED} 项，失败 {len(FAILED)} 项")
    if FAILED:
        print("\n失败项：")
        for item in FAILED:
            print(f"  - {item}")
        return 1
    print("全部通过：后端在实际 HTTP 环境下行为符合作业要求。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
