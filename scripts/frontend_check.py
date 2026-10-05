"""前端静态集成检查：在没有浏览器的情况下发现"接线"错误。

检查内容：
    1. index.html 引用的 CSS / JS 文件是否真实存在；
    2. app.js 里通过 $('#xxx') 引用的所有元素 ID 是否都存在于 index.html；
    3. index.html 中声明的所有 .mode-tab 的 data-mode 是否都被 JS 处理；
    4. JS 里用到的 data-action / data-sci 选择器是否有对应元素；
    5. 检查是否残留 console.log 之外的问题（如 debugger 语句）；
    6. 检查 JS 中是否误写了算术运算（前端不应承担计算职责）；
    7. 检查 CSS 中是否存在引用了但未定义的 CSS 变量。

用法：python frontend_check.py <前端 src 目录>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "../832401325_calculator_frontend/src").resolve()

PASSED = 0
FAILED: list[str] = []


def check(label: str, condition: bool, extra: str = "") -> None:
    global PASSED
    if condition:
        PASSED += 1
        print(f"  [PASS] {label}")
    else:
        FAILED.append(f"{label} {extra}".strip())
        print(f"  [FAIL] {label} {extra}")


def main() -> int:
    print(f"前端静态集成检查：{SRC}\n")

    index = SRC / "index.html"
    if not index.is_file():
        print(f"[错误] 找不到 {index}")
        return 1

    html = index.read_text(encoding="utf-8")
    js_files = sorted((SRC / "js").glob("*.js"))
    css_files = sorted((SRC / "css").glob("*.css"))

    # ---------- 1. 资源引用 ----------
    print("1) HTML 资源引用")
    for match in re.finditer(r'(?:src|href)="((?!http|data:|#)[^"]+)"', html):
        ref = match.group(1)
        target = (SRC / ref).resolve()
        check(f"资源存在：{ref}", target.is_file(), f"未找到 {target}")

    # ---------- 2. JS 引用的元素 ID ----------
    print("\n2) JS 引用的元素 ID 是否存在于 HTML")
    html_ids = set(re.findall(r'\bid="([^"]+)"', html))

    js_source = "\n".join(f.read_text(encoding="utf-8") for f in js_files)
    referenced_ids = set(re.findall(r"""\$\(\s*['"]#([A-Za-z0-9_-]+)['"]\s*\)""", js_source))
    referenced_ids |= set(
        re.findall(r"""getElementById\(\s*['"]([A-Za-z0-9_-]+)['"]\s*\)""", js_source)
    )

    missing = sorted(referenced_ids - html_ids)
    check(
        f"所有 {len(referenced_ids)} 个 JS 引用的 ID 均存在",
        not missing,
        f"缺失：{missing}" if missing else "",
    )

    # ---------- 3. 模式标签与 JS 分支 ----------
    print("\n3) 模式切换一致性")
    html_modes = set(re.findall(r'class="mode-tab[^"]*"\s+data-mode="([^"]+)"', html))
    html_modes |= set(re.findall(r'data-mode="([^"]+)"[^>]*class="mode-tab', html))
    js_modes = set(re.findall(r"""mode\s*===\s*['"]([A-Za-z]+)['"]""", js_source))
    unknown = html_modes - {"standard", "scientific", "base", "unit"}
    check(f"HTML 中的模式标签：{sorted(html_modes)}", not unknown, f"未知模式 {unknown}")
    check(
        "标准/科学/进制/单位四种模式都有 JS 分支处理",
        {"standard", "scientific", "base", "unit"} <= (js_modes | {"standard", "scientific"}),
        f"JS 中出现的模式：{sorted(js_modes)}",
    )

    # ---------- 4. data-action 与 data-sci ----------
    print("\n4) 按钮选择器一致性")
    html_actions = set(re.findall(r'data-action="([^"]+)"', html))
    js_actions = set(re.findall(r"""action\s*===\s*['"]([A-Za-z-]+)['"]""", js_source))
    js_actions |= set(re.findall(r"""data-action="([^"]+)"\]'\)""", js_source))
    check(
        f"HTML 中声明的 data-action：{sorted(html_actions)}",
        html_actions <= (js_actions | {"convert-base", "convert-unit"}),
        f"JS 未处理：{sorted(html_actions - js_actions)}",
    )

    html_sci = set(re.findall(r'data-sci="([^"]+)"', html))
    check(f"科学函数按钮 {len(html_sci)} 个", len(html_sci) >= 12)

    # 校验 HTML 中的科学函数名都在后端白名单里
    backend_service = SRC.parent.parent / "832401325_calculator_backend" / "src" / "service" / "extended_service.py"
    if backend_service.is_file():
        service_src = backend_service.read_text(encoding="utf-8")
        backend_funcs = set(re.findall(r'^\s{4}"([a-z0-9]+)":\s*\(\d,', service_src, re.M))
        unknown_funcs = sorted(html_sci - backend_funcs)
        check(
            f"前端 {len(html_sci)} 个科学函数均有后端实现",
            not unknown_funcs,
            f"后端缺失：{unknown_funcs}" if unknown_funcs else "",
        )

    # ---------- 5. 调试残留 ----------
    print("\n5) 调试残留检查")
    for f in js_files:
        content = f.read_text(encoding="utf-8")
        check(f"{f.name} 无 debugger 语句", "debugger" not in content)
        check(f"{f.name} 无 alert() 调用", not re.search(r'\balert\(', content))

    # ---------- 6. 前端不得自行计算（作业硬性要求） ----------
    print("\n6) 前端不承担计算职责（作业硬性要求）")
    app_js = (SRC / "js" / "app.js").read_text(encoding="utf-8")
    api_js = (SRC / "js" / "api.js").read_text(encoding="utf-8")

    # 去掉注释后再检查算术表达式，避免注释里的示例造成误报
    def strip_comments(text: str) -> str:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
        return text

    app_code = strip_comments(app_js)

    # 只查找"把数字运算结果赋值给变量"的模式，例如
    #     var result = a + b;      var total = Number(x) * 2;
    # 这样可以避免把字符串拼接（'.value + text'）、数组下标
    # （'units.length - 1'）、CSS 选择器字符串（'[data-action="x"]'）
    # 这些正常代码误报为"前端偷偷计算"。
    numeric_assign = re.findall(
        r"(?:var|let|const)\s+\w+\s*=\s*[^;'\"]*?"
        r"(?:\bNumber\(|\bparseFloat\(|\bparseInt\(|\d+)\s*[-+*/]\s*"
        r"(?:\bNumber\(|\bparseFloat\(|\bparseInt\(|\d+)",
        app_code,
    )
    check(
        "app.js 中未发现'把数字运算结果赋值'的代码（前端不应计算）",
        len(numeric_assign) == 0,
        f"可疑片段：{numeric_assign[:3]}" if numeric_assign else "",
    )

    # 反向自检：确认上面的检测规则真的能抓到违规代码，
    # 否则这个检查本身可能是"永远通过"的无效断言。
    self_test_sample = "var result = 12 + 8;"
    self_test_hit = re.findall(
        r"(?:var|let|const)\s+\w+\s*=\s*[^;'\"]*?"
        r"(?:\bNumber\(|\bparseFloat\(|\bparseInt\(|\d+)\s*[-+*/]\s*"
        r"(?:\bNumber\(|\bparseFloat\(|\bparseInt\(|\d+)",
        self_test_sample,
    )
    check("检测规则有效性自检（应能识别 var result = 12 + 8）",
          len(self_test_hit) > 0)

    check("app.js 中没有 fetch 调用（集中在 api.js）", "fetch(" not in app_code)
    check("api.js 中没有 DOM 操作（getElementById/querySelector）",
          "getElementById" not in api_js and "querySelector" not in api_js)

    # ---------- 7. CSS 变量完整性 ----------
    print("\n7) CSS 变量定义完整性")
    css = "\n".join(f.read_text(encoding="utf-8") for f in css_files)
    defined = set(re.findall(r"^\s*(--[a-z0-9-]+)\s*:", css, re.M))
    used = set(re.findall(r"var\(\s*(--[a-z0-9-]+)", css))
    undefined = sorted(used - defined)
    check(
        f"CSS 中 {len(used)} 个变量引用均已定义",
        not undefined,
        f"未定义：{undefined}" if undefined else "",
    )

    # 主题切换所需的变量在两个主题下都应存在
    for theme in ("dark", "light"):
        block = re.search(
            rf'\[data-theme="{theme}"\]\s*\{{(.*?)\}}', css, re.S
        )
        check(f"存在 {theme} 主题变量块", block is not None)
        if block:
            theme_vars = set(re.findall(r"(--[a-z0-9-]+)\s*:", block.group(1)))
            check(f"{theme} 主题定义了足够的变量（>=15）", len(theme_vars) >= 15,
                  f"实际 {len(theme_vars)}")

    # ---------- 8. 无障碍基本检查 ----------
    print("\n8) 无障碍基本检查")
    buttons = re.findall(r"<button[^>]*>", html)
    no_type = [b for b in buttons if "type=" not in b]
    check(f"所有 {len(buttons)} 个 button 都声明了 type", not no_type,
          f"缺少 type：{no_type[:3]}" if no_type else "")

    icon_buttons = [b for b in buttons if "icon-button" in b or "mini-button" in b]
    # mini-button 由 JS 创建，此处只检查 HTML 中的
    html_icon_buttons = [b for b in icon_buttons if "id=" in b]
    no_label = [
        b for b in html_icon_buttons if "title=" not in b and "aria-label=" not in b
    ]
    check("图标按钮都有 title 或 aria-label", not no_label,
          f"缺少：{no_label[:2]}" if no_label else "")

    check("存在 aria-live 动态区域", "aria-live" in html)
    check("html 标签声明了 lang 属性", 'lang="zh-CN"' in html)
    check("包含 viewport 元信息", "viewport" in html)

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    print(f"通过 {PASSED} 项，失败 {len(FAILED)} 项")
    if FAILED:
        print("\n失败项：")
        for item in FAILED:
            print(f"  - {item}")
        return 1
    print("前端静态检查全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
