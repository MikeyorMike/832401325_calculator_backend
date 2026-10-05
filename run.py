"""本地启动脚本：python run.py。

集成了 uvicorn，避免依赖命令行参数，方便不熟悉终端的同学使用。
"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    # 云平台通常通过 PORT 环境变量指定端口，本地默认 8000
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "true").lower() == "true"

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload_enabled,
    )
