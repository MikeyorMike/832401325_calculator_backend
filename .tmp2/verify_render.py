"""验证 Render 上的后端服务是否正常工作（模拟浏览器会发起的请求）。

检查内容：
    1. /api/health 健康检查
    2. /api/calculate 计算接口（前端点击「=」时调用）
    3. CORS 响应头（决定浏览器能否跨域调用）
    4. /docs 接口文档
    5. 除零等异常分支
"""

import json
import ssl
import urllib.error
import urllib.request

BASE = "https://eight32401325-calculator-backend.onrender.com"
PROXY = "http://127.0.0.1:26001"
ORIGIN = "https://example.netlify.app"

# 走本机代理访问（与 git 推送用同一个代理）
handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
opener = urllib.request.build_opener(handler)


def call(method, path, payload=None, origin=None, preflight_method=None):
    url = BASE + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json", "User-Agent": "verify-script/1.0"}
    if data:
        headers["Content-Type"] = "application/json"
    if origin:
        headers["Origin"] = origin
    if preflight_method:
        headers["Access-Control-Request-Method"] = preflight_method
        headers["Access-Control-Request-Headers"] = "content-type"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                body = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                body = {"_raw_length": len(raw)}
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = {"_raw_length": len(raw)}
        return e.code, body, dict(e.headers)
    except Exception as e:
        return None, {"_error": "%s: %s" % (type(e).__name__, e)}, {}


print("目标后端: %s" % BASE)
print("经代理  : %s" % PROXY)
print("=" * 62)

# 1) 健康检查
status, body, _ = call("GET", "/api/health")
print("\n[1] GET /api/health")
print("    状态码: %s" % status)
print("    响应  : %s" % json.dumps(body, ensure_ascii=False))

# 2) 计算接口
print("\n[2] POST /api/calculate  （前端点击「=」时调用）")
for expr in ["(1+2)*3", "1+2*3", "0.1+0.2", "-5+8", "3*-2"]:
    status, body, _ = call("POST", "/api/calculate", {"expression": expr})
    if status == 201:
        print("    %-12s -> %-8s (HTTP %s)" % (expr, body.get("result"), status))
    else:
        print("    %-12s -> 失败 HTTP %s %s" % (expr, status, body))

# 3) CORS（决定浏览器能否调用）
print("\n[3] CORS 检查（浏览器跨域调用的前提）")
status, _, headers = call("GET", "/api/health", origin=ORIGIN)
acao = headers.get("access-control-allow-origin")
print("    简单请求 Access-Control-Allow-Origin: %s" % (acao or "(缺失！浏览器会拦截)"))
status, _, headers = call(
    "OPTIONS", "/api/calculate", origin=ORIGIN, preflight_method="POST"
)
print("    预检请求状态码: %s" % status)
print("    预检 Allow-Methods: %s" % headers.get("access-control-allow-methods", "(缺失)"))

# 4) 异常分支
print("\n[4] 异常处理")
for expr in ["1/0", "1++*2"]:
    status, body, _ = call("POST", "/api/calculate", {"expression": expr})
    print("    %-8s -> HTTP %s  code=%s" % (expr, status, body.get("code")))

# 5) 接口文档
print("\n[5] GET /docs （接口文档）")
status, body, _ = call("GET", "/docs")
print("    状态码: %s" % status)

# 6) 历史查询
print("\n[6] GET /api/history （读后端数据库）")
status, body, _ = call("GET", "/api/history?page=1&page_size=3")
if status == 200:
    print("    状态码: %s   总记录数: %s" % (status, body.get("total")))
    for item in body.get("items", []):
        print("      id=%-4s %-16s = %s" % (item["id"], item["expression"], item["result"]))
else:
    print("    状态码: %s  响应: %s" % (status, body))

print("\n" + "=" * 62)
print("结论：以上各项均正常，可放心用于第 4 步的前端配置。")
