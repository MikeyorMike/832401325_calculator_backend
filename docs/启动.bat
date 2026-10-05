@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  前后端分离计算器系统 —— 一键启动脚本
REM
REM  功能：
REM    1. 检查 Python 环境
REM    2. 首次运行时自动创建虚拟环境并安装依赖
REM    3. 分别启动后端（8000 端口）与前端（5500 端口）服务
REM    4. 自动打开浏览器
REM
REM  使用：双击本文件即可
REM ============================================================

set "BACKEND_DIR=%~dp0..\832401325_calculator_backend"
set "FRONTEND_DIR=%~dp0..\832401325_calculator_frontend\src"

echo.
echo ============================================================
echo   前后端分离计算器系统 - 本地启动
echo ============================================================
echo.

REM ---------- 1. 检查 Python ----------
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python。
    echo.
    echo 请先安装 Python 3.11 或更高版本：https://www.python.org/downloads/
    echo 安装时务必勾选 "Add Python to PATH"。
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
echo [1/4] 已检测到 Python %PY_VERSION%

REM ---------- 2. 检查目录 ----------
if not exist "%BACKEND_DIR%\run.py" (
    echo [错误] 找不到后端项目目录：
    echo        %BACKEND_DIR%
    echo.
    echo 请确认两个项目文件夹位于同一个父目录下。
    pause
    exit /b 1
)
echo [2/4] 后端目录：%BACKEND_DIR%

REM ---------- 3. 准备虚拟环境与依赖 ----------
cd /d "%BACKEND_DIR%"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [3/4] 首次运行，正在创建虚拟环境并安装依赖...
    echo       这可能需要 1~2 分钟，请耐心等待。
    echo.
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败。
        pause
        exit /b 1
    )
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip -q
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败。请检查网络连接后重试。
        echo        离线环境下可尝试国内镜像：
        echo        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        echo.
        pause
        exit /b 1
    )
    echo.
    echo       依赖安装完成。
) else (
    echo [3/4] 虚拟环境已存在，跳过依赖安装
    call ".venv\Scripts\activate.bat"
)

REM ---------- 4. 启动服务 ----------
echo.
echo [4/4] 正在启动服务...
echo.

REM 后端：新开窗口运行，便于直接看到接口请求日志
start "计算器后端 (端口 8000)" cmd /k "cd /d "%BACKEND_DIR%" && call .venv\Scripts\activate.bat && python run.py"

REM 等待后端完成初始化
echo       正在等待后端启动...
timeout /t 6 /nobreak >nul

REM 前端：新开窗口运行静态服务器
start "计算器前端 (端口 5500)" cmd /k "cd /d "%FRONTEND_DIR%" && python -m http.server 5500"

REM 再等前端就绪
timeout /t 3 /nobreak >nul

echo.
echo ============================================================
echo   启动完成！
echo ============================================================
echo.
echo   前端页面    http://127.0.0.1:5500
echo   后端文档    http://127.0.0.1:8000/docs
echo   健康检查    http://127.0.0.1:8000/api/health
echo.
echo   提示：
echo     - 已弹出两个命令行窗口，关闭它们即停止对应服务
echo     - 页面顶部显示绿点「后端已连接」即为成功
echo     - 关闭本窗口不影响服务运行
echo.
echo ============================================================
echo.

REM 自动打开浏览器
start "" "http://127.0.0.1:5500"

echo 按任意键关闭本窗口（服务会继续运行）...
pause >nul

endlocal
