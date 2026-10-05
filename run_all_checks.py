"""一键运行全部检查。

用法（在本目录执行）：
    python run_all_checks.py

依次执行：
    1. 后端单元测试 + API 集成测试（111 个用例）
    2. 前端静态集成检查（HTML/JS/CSS 接线正确性）
    3. 若后端服务已在运行，额外执行端到端 HTTP 验证（44 项断言）

说明：
    第 3 步需要后端已经启动。脚本会先探测端口，未启动则跳过并给出提示，
    不会因为服务没起而报错。
"""

from __future__ import annotations

import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT.parent / "832401325_calculator_frontend" / "src"
BASE_URL = "http://127.0.0.1:8000"


def run(title: str, args: list[str]) -> int:
    """执行一条命令并打印结果。"""
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print(f"{'=' * 62}")
    result = subprocess.run(args, cwd=str(ROOT), check=False)
    return result.returncode


def backend_is_up() -> bool:
    """探测后端是否已在运行。"""
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=3) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


def main() -> int:
    failures: list[str] = []

    # ---------- 1. 后端测试 ----------
    code = run(
        "1/3  后端测试（表达式引擎 + API + 扩展功能）",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
    )
    if code != 0:
        failures.append("后端测试")

    # ---------- 2. 前端静态检查 ----------
    code = run(
        "2/3  前端静态集成检查",
        [sys.executable, "scripts/frontend_check.py", str(FRONTEND)],
    )
    if code != 0:
        failures.append("前端静态检查")

    # ---------- 3. 端到端验证（可选） ----------
    if backend_is_up():
        code = run(
            "3/3  端到端 HTTP 验证（针对正在运行的服务）",
            [sys.executable, "scripts/e2e_check.py", BASE_URL],
        )
        if code != 0:
            failures.append("端到端验证")
    else:
        print(f"\n{'=' * 62}")
        print("  3/3  端到端验证 —— 已跳过")
        print(f"{'=' * 62}")
        print(f"  未检测到 {BASE_URL} 上运行的后端服务。")
        print("  如需执行端到端验证，请先启动后端：")
        print("      python run.py")
        print("  然后重新运行本脚本。")

    # ---------- 汇总 ----------
    print(f"\n{'=' * 62}")
    if failures:
        print("  检查结果：存在失败项")
        for item in failures:
            print(f"    ✗ {item}")
        print(f"{'=' * 62}")
        return 1

    print("  检查结果：全部通过 ✓")
    print(f"{'=' * 62}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
