"""测试包。

运行方式（在项目根目录）：
    python -m unittest discover -s tests -v
"""

import os
import sys
from pathlib import Path

# 把项目根目录加入模块搜索路径，同时把 _vendor（本地依赖目录）
# 也加进去，这样在没有全局安装依赖时测试也能跑起来。
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_VENDOR = ROOT / "_vendor"
if _VENDOR.is_dir():
    sys.path.append(str(_VENDOR))

# 测试期间使用独立的临时数据库，避免污染开发数据库
os.environ.setdefault("DATABASE_PATH", str(ROOT / "data" / "test_calculator.db"))
