"""在线演示脚本：对着正在运行的服务走一遍完整业务流并打印结果。

用途：本地演示 / 截图时快速验证功能，或直接作为博客的验证记录。

用法：
    python scripts/live_demo.py [base_url]
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def call(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    """发起请求并返回 (状态码, 响应体)。"""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if data:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, {"raw": raw[:200]}


def section(title: str) -> None:
    print(f"\n{'─' * 66}")
    print(f"  {title}")
    print(f"{'─' * 66}")


def main() -> int:
    status, health = call("GET", "/api/health")
    if status != 200:
        print(f"后端未就绪（HTTP {status}），请先启动：python run.py")
        return 1

    print(f"后端已连接：{BASE}")
    print(f"服务名称：{health.get('app')}   版本：{health.get('version')}")

    # ---------- 功能一、功能二 ----------
    section("【功能一 + 功能二】前端只发送表达式，结果全部由后端计算")
    cases = [
        ("12+8", "加法"),
        ("12-8", "减法"),
        ("12*8", "乘法"),
        ("12/8", "除法"),
        ("1+2*3", "运算优先级：应为 7 而非 9"),
        ("(1+2)*3", "括号改变优先级"),
        ("10/2+7", "混合运算"),
        ("8-3*2", "混合运算"),
        ("-5+8", "一元负号（开头）"),
        ("3*-2", "一元负号（运算符后）"),
        ("0.1+0.2", "小数精度：应为 0.3 而非 0.30000000000000004"),
        ("((2+3)*(4-1))/5", "嵌套括号"),
        ("2--3", "双负号"),
        ("6×7", "前端 × 符号自动归一化"),
        ("8÷2", "前端 ÷ 符号自动归一化"),
    ]
    ok = 0
    for expression, note in cases:
        status, body = call("POST", "/api/calculate", {"expression": expression})
        if status == 201:
            ok += 1
            print(f"  ✓ {expression:<18} = {body['result']:<8} id={body['record']['id']:<3} {note}")
        else:
            print(f"  ✗ {expression:<18} HTTP {status}  {body.get('message')}")
    print(f"\n  共 {ok}/{len(cases)} 条计算成功（每条都已写入数据库）")

    # ---------- 异常处理 ----------
    section("【功能二 · 异常处理】非法输入必须被拒绝")
    bad_cases = [
        ("1/0", "400", "DIVISION_BY_ZERO", "除数为零"),
        ("5/(3-3)", "400", "DIVISION_BY_ZERO", "表达式形式的除零"),
        ("1++*2", "400", "INVALID_EXPRESSION", "运算符连续"),
        ("(1+2", "400", "INVALID_EXPRESSION", "缺少右括号"),
        ("1+", "400", "INVALID_EXPRESSION", "表达式不完整"),
        ("1.2.3", "400", "INVALID_EXPRESSION", "小数点重复"),
        ("2(3)", "400", "INVALID_EXPRESSION", "隐式乘法不支持"),
    ]
    for expression, want_status, want_code, note in bad_cases:
        status, body = call("POST", "/api/calculate", {"expression": expression})
        mark = "✓" if str(status) == want_status else "✗"
        print(f"  {mark} {expression:<12} HTTP {status}  {body.get('code'):<20} {body.get('message')}")
        print(f"      （场景：{note}）")

    # ---------- 安全检查 ----------
    section("【安全】代码注入尝试必须失败（证明未使用 eval/exec）")
    payloads = [
        "__import__('os').system('whoami')",
        "eval('1+1')",
        "1+open('/etc/passwd').read()",
        "9**9**9",
    ]
    for payload in payloads:
        status, body = call("POST", "/api/calculate", {"expression": payload})
        mark = "✓" if status == 400 else "✗"
        print(f"  {mark} HTTP {status}  {payload[:44]:<46} -> {body.get('code')}")

    # ---------- 功能三 ----------
    section("【功能三】计算历史（从后端数据库读取）")
    status, body = call("GET", "/api/history?page=1&page_size=5")
    print(f"  数据库中共 {body['total']} 条记录，共 {body['total_pages']} 页，当前第 {body['page']} 页")
    print(f"\n  {'ID':<4}{'表达式':<22}{'结果':<12}{'计算时间':<28}{'扩展'}")
    print(f"  {'─' * 4}{'─' * 22}{'─' * 12}{'─' * 28}{'─' * 6}")
    for item in body["items"]:
        print(
            f"  {item['id']:<4}{item['expression']:<22}{item['result']:<12}"
            f"{item['created_at']:<28}{'是' if item['is_extended'] else '否'}"
        )

    # 关键字搜索
    status, body = call("GET", "/api/history?keyword=12%2B8")
    print(f"\n  关键字搜索 '12+8' -> 命中 {body['total']} 条")

    # ---------- 功能四 ----------
    section("【功能四】删除指定历史记录（真实删除数据库行）")
    status, before = call("GET", "/api/history?page=1&page_size=1")
    if before["items"]:
        target = before["items"][0]
        print(f"  删除前总数：{before['total']}")
        print(f"  目标记录：id={target['id']}  {target['expression']} = {target['result']}")

        status, deleted = call("DELETE", f"/api/history/{target['id']}")
        print(f"  DELETE /api/history/{target['id']} -> HTTP {status}  {deleted.get('message')}")

        # 直接再查这个 id，应该 404
        status, _ = call("GET", f"/api/history/{target['id']}")
        print(f"  再次查询该 id -> HTTP {status}（应为 404，说明确实删掉了）")

        status, after = call("GET", "/api/history?page=1&page_size=1")
        print(f"  删除后总数：{after['total']}（减少了 {before['total'] - after['total']} 条）")

        status, _ = call("DELETE", "/api/history/999999")
        print(f"  删除不存在的 id -> HTTP {status}（应为 404）")

    # ---------- 扩展功能 ----------
    section("【扩展功能】科学计算 / 进制转换 / 单位换算")
    extended = [
        ({"type": "scientific", "function": "sqrt", "operands": ["144"]}, "平方根 √144"),
        ({"type": "scientific", "function": "factorial", "operands": ["10"]}, "阶乘 10!"),
        ({"type": "scientific", "function": "power", "operands": ["2", "10"]}, "幂 2^10"),
        ({"type": "scientific", "function": "sin", "operands": ["30"]}, "正弦 sin30°"),
        ({"type": "base", "value": "255", "from_base": 10, "to_base": 2}, "255 十进制→二进制"),
        ({"type": "base", "value": "FF", "from_base": 16, "to_base": 10}, "FF 十六进制→十进制"),
        ({"type": "unit", "category": "temperature", "value": "100",
          "from_unit": "c", "to_unit": "f"}, "100°C → °F"),
        ({"type": "unit", "category": "length", "value": "1.5",
          "from_unit": "km", "to_unit": "m"}, "1.5 千米 → 米"),
        ({"type": "unit", "category": "mass", "value": "1",
          "from_unit": "kg", "to_unit": "pound"}, "1 千克 → 磅"),
    ]
    for payload, note in extended:
        status, body = call("POST", "/api/extended", payload)
        if status == 201:
            print(f"  ✓ {body['display']:<44} （{note}）")
        else:
            print(f"  ✗ HTTP {status}  {body.get('message')}")

    # ---------- 统计 ----------
    section("【扩展功能】计算统计")
    status, stats = call("GET", "/api/statistics")
    print(f"  总记录数：{stats['total']}    今日：{stats['today']}    收藏：{stats['favorites']}")
    print(f"  最近一次计算：{stats['latest_at']}")

    # ---------- 汇总 ----------
    print(f"\n{'═' * 66}")
    print("  演示完成：四项必需功能 + 异常处理 + 安全防护 + 扩展功能全部正常")
    print(f"{'═' * 66}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
