# 代码规范（后端）

> 本文件是「前后端分离计算器系统」**后端项目**的代码规范说明。

## 规范来源

本规范来源于以下主流官方规范，并结合本项目实际情况做了取舍与细化：

| 来源 | 链接 | 采用情况 |
| --- | --- | --- |
| **PEP 8 – Style Guide for Python Code** | <https://peps.python.org/0008/> | **主要依据**，命名、缩进、行长、空行等全部遵循 |
| **PEP 257 – Docstring Conventions** | <https://peps.python.org/0257/> | 采纳，所有公开模块/类/函数均写文档字符串 |
| **Google Python Style Guide** | <https://google.github.io/styleguide/pyguide.html> | 采纳其类型注解、导入顺序、异常处理建议 |
| **PEP 484 / 604 – Type Hints** | <https://peps.python.org/0484/> | 采纳，所有函数签名标注类型 |

本项目**不引入** `black` / `flake8` / `ruff` 等格式化工具作为强制门禁，
原因是作业环境可能无法联网安装额外工具；
但代码本身遵守下表全部规则，可直接用 `black --check` 通过校验。

---

## 1. 命名规范（PEP 8）

| 对象 | 规则 | 示例 |
| --- | --- | --- |
| 模块 / 包 | 全小写，单词间用下划线 | `calculator.py`、`history_repository.py` |
| 类 | 大驼峰（CapWords） | `Parser`、`TokenType`、`AppError` |
| 函数 / 方法 | 全小写 + 下划线 | `evaluate()`、`list_history()`、`validate_expression()` |
| 变量 | 全小写 + 下划线 | `expression`、`record_id`、`total_pages` |
| 常量 | 全大写 + 下划线 | `SCHEMA_SQL`、`NUMBER_PATTERN`、`_COLUMNS` |
| 私有成员 | 单下划线前缀 | `_connect()`、`_row_to_dict()`、`self._cursor` |
| 异常类 | 大驼峰，以 `Error` 结尾 | `ExpressionError`、`RecordNotFoundError` |
| Pydantic 模型 | 大驼峰，语义后缀 | `CalculateRequest`、`HistoryListResponse` |

**禁止**：单字符命名（循环计数 `i` 除外）、无意义缩写（`calc_expr_rslt`）、
拼音命名（`jisuan`）、与内置名冲突（`list`、`dict`、`type`）。

---

## 2. 格式规范

### 2.1 缩进与行长

- 缩进使用 **4 个空格**，禁止 Tab
- 单行不超过 **88 个字符**（与 `black` 默认一致，略宽于 PEP 8 的 79）
- 续行使用**悬挂缩进**，与开括号后第一个参数对齐：

```python
# 正确
result = history_service.list_history(
    page=page,
    page_size=page_size,
    keyword=keyword,
)

# 错误：续行与开括号内容不对齐
result = history_service.list_history(page=page,
    page_size=page_size)
```

### 2.2 空行

- 顶层函数/类之间：**2 个空行**
- 类内方法之间：**1 个空行**
- 函数内部逻辑分组之间：**1 个空行**
- 文件末尾：保留 **1 个换行**，不留多余空行

```python
class Parser:
    """解析器。"""

    def parse(self) -> Decimal:
        """入口方法。"""
        ...

    def _parse_expression(self) -> Decimal:
        """处理加减。"""
        ...


def evaluate(raw_expression: str) -> dict[str, object]:
    """模块级函数，与上一个定义之间空两行。"""
    ...
```

### 2.3 导入顺序

按以下三组排列，组间空一行（Google 风格 + PEP 8）：

```python
# 1. 标准库
from __future__ import annotations

import logging
import re
from decimal import Decimal
from enum import Enum

# 2. 第三方库
from fastapi import APIRouter, Path, Query

# 3. 本项目模块
from src.core.config import settings
from src.core.exceptions import ExpressionError
```

**规则**：
- 一律使用**绝对导入**（`from src.core.config import settings`），不使用相对导入
- 每个导入一行，禁止 `import a, b`
- 禁止 `from x import *`
- 模块顶部统一写 `from __future__ import annotations`，以支持延迟求值的类型注解

### 2.4 字符串

- 统一使用**双引号** `"..."`；字符串内含双引号时改用单引号
- 多行文本用三双引号 `"""..."""`
- **禁止**在 f-string 中使用反斜杠（Python < 3.12 不允许），必要时用字符串拼接

```python
# 正确
raise ExpressionError(f"位置 {index + 1} 处的数字格式不正确")
raise ExpressionError("表达式包含非法字符：" + "、".join(sorted(illegal)))

# 错误（Python 3.11 及以下会报 SyntaxError）
raise ExpressionError(f"非法字符：{'、'.join(sorted(illegal))}")
```

### 2.5 尾随逗号

多行容器（列表、字典、函数调用、函数参数）**必须**使用尾随逗号，
这样新增元素时 diff 只显示一行变更：

```python
SCIENTIFIC_FUNCTIONS: dict[str, tuple[int, Any]] = {
    "sqrt": (1, _sqrt),
    "square": (1, lambda v: _to_float(v) ** 2),
}
```

---

## 3. 类型注解（PEP 484 / 604）

**所有函数与方法**（含测试辅助函数）必须标注参数与返回值类型。

```python
# 正确：使用 PEP 604 的 | 语法
def evaluate(raw_expression: str) -> dict[str, object]:
    ...

def get_history_by_id(record_id: int) -> dict[str, Any] | None:
    ...

# 正确：内置泛型直接下标，无需 typing.List / Dict
def list_history(...) -> list[dict[str, Any]]:
    ...

# 错误：缺少注解
def evaluate(raw_expression):
    ...
```

**规则**：
- 使用 `list[str]` / `dict[str, int]`，**不用** `List[str]` / `Dict[str, int]`
- 可选值用 `X | None`，**不用** `Optional[X]`
- 复杂容器类型必须写出元素类型，禁止裸 `list` / `dict`
- 私有辅助函数同样需要注解

---

## 4. 文档字符串（PEP 257）

**所有模块、公开类、公开函数**必须有 docstring，使用三双引号。

### 4.1 模块级

首行简要说明模块职责；较复杂的模块（如 `calculator.py`）补充设计说明。

```python
"""表达式解析与求值引擎（本项目的核心模块）。

================================================================
设计要点
================================================================

1. 为什么不用 eval / exec？
   ...
2. 整体流程
   原始字符串 -> tokenize() -> Token 序列 -> Parser.parse() -> Decimal
"""
```

### 4.2 函数级

首行一句话说明用途，空一行后补充说明；含参数的函数使用该格式：

```python
def delete_history(record_id: int) -> None:
    """删除指定历史记录；记录不存在时抛 404 领域异常。

    Args:
        record_id: 历史记录主键 ID。

    Raises:
        RecordNotFoundError: 指定 ID 的记录不存在。
    """
```

**规则**：
- 首行为祈使句，以句号结尾，不超过一行
- 参数不多于 1 个且含义显然时，可省略 `Args:` 段落
- 会抛异常的函数必须写 `Raises:`
- 无返回值的函数（`-> None`）不写 `Returns:`

### 4.3 注释

- 注释说明**为什么这样做**，而不是重复代码在做什么
- 行内注释与代码之间至少 **2 个空格**
- 复杂逻辑前用块注释分段说明

```python
# 正确：解释了「为什么」
# 先归一化去掉尾随零，再用定点格式输出，避免出现 1E+2 这种写法
normalized = value.normalize()

# 错误：只是复述代码
# 归一化 value
normalized = value.normalize()
```

---

## 5. 异常处理

### 5.1 自定义异常层次

项目使用统一的领域异常体系，定义在 `src/core/exceptions.py`：

```
AppError                     # 基类，携带 code / message / status_code
├── ExpressionError          # 400 表达式非法
│   ├── DivisionByZeroError  # 400 除数为零
│   ├── ExpressionTooLongError
│   └── ResultOverflowError
├── RecordNotFoundError      # 404 记录不存在
└── DatabaseError            # 500 数据库错误
```

### 5.2 规则

1. **业务层只抛领域异常**，不抛 `HTTPException`（避免业务逻辑依赖 Web 框架）
2. **接口层统一翻译**，在 `main.py` 的异常处理器中转换为 HTTP 响应
3. **禁止裸 `except:`**，必须指明异常类型
4. 捕获后若无法处理，须保留原始异常链：

```python
# 正确：保留异常链，便于排查
except InvalidOperation as exc:
    raise ExpressionError(f"无法识别的数字 '{token.text}'") from exc

# 错误：丢失了原始异常信息
except InvalidOperation:
    raise ExpressionError("数字错误")

# 错误：裸 except 会吞掉 KeyboardInterrupt 和 SystemExit
except:
    pass
```

5. **异常信息面向用户**，不要泄露内部实现或 SQL 细节
6. 仅在**能真正处理**时才捕获异常，否则让它向上传播

---

## 6. 数据库访问规范

1. **所有 SQL 只出现在 `repository/` 层**，`service/` 与 `api/` 不得出现 SQL
2. **必须使用参数化查询**，禁止字符串拼接 SQL（防 SQL 注入）：

```python
# 正确
connection.execute(
    "SELECT id FROM calculation_history WHERE id = ?", (record_id,)
)

# 严禁：存在 SQL 注入风险
connection.execute(f"SELECT * FROM calculation_history WHERE id = {record_id}")
```

3. **必须使用上下文管理器**管理连接，保证提交/回滚/关闭：

```python
with get_connection() as connection:
    connection.execute(...)
```

4. **禁止 `SELECT *`**，显式列出列名（本项目统一用 `_COLUMNS` 常量）
5. 返回类型统一为**字典或字典列表**，不把 `sqlite3.Row` 泄露到上层
6. 布尔值在 SQLite 中以 `INTEGER` 0/1 存储，出库时转回 `bool`

---

## 7. 接口层规范

1. 路由函数**只做三件事**：解析参数 → 调用业务层 → 组装响应模型
2. 每个路由**必须声明 `response_model`**，保证响应结构受约束并可生成文档
3. 每个路由**必须写 `summary` 与 `description`**，便于助教在 `/docs` 中阅读
4. 使用 `Path(..., ge=1)` / `Query(..., le=100)` 做参数边界校验
5. 错误响应通过 `responses={}` 显式声明，使 OpenAPI 文档完整

```python
@router.delete(
    "/history/{record_id}",
    response_model=schemas.DeleteResponse,
    summary="删除指定历史记录",
    description="从数据库中真实删除该记录。",
    responses={404: {"model": schemas.ErrorResponse, "description": "记录不存在"}},
)
def delete_history_item(
    record_id: int = Path(..., ge=1, description="历史记录 ID"),
) -> schemas.DeleteResponse:
    history_service.delete_history(record_id)
    return schemas.DeleteResponse(
        message=f"已删除历史记录 id={record_id}", deleted_id=record_id
    )
```

---

## 8. 安全规范

| 规则 | 说明 |
| --- | --- |
| **禁止 `eval` / `exec`** | 表达式必须通过词法分析 + 语法分析处理 |
| **禁止拼接 SQL** | 全部使用参数化查询 |
| **输入白名单校验** | 表达式只允许 `0-9 . + - * / ( )` 与空白字符 |
| **长度限制** | 表达式 ≤ 200 字符，单个操作数 ≤ 64 字符，防止资源耗尽 |
| **结果范围限制** | 绝对值超过 `1e100` 判为溢出并报错 |
| **函数名白名单** | 扩展功能的科学函数必须在 `SCIENTIFIC_FUNCTIONS` 字典内 |
| **错误信息脱敏** | 500 错误只记录日志，对外统一返回「服务器内部错误」 |

测试中通过 `test_no_eval_in_source` 与 `test_code_injection_is_rejected`
对上述约定做**自动化回归保护**。

---

## 9. 测试规范

1. 测试文件放在 `tests/` 目录，命名 `test_<模块名>.py`
2. 测试类命名 `Test<被测功能>`，方法命名 `test_<具体行为>`
3. 测试方法名应能**直接读出断言内容**：

```python
def test_division_by_zero_returns_400_with_specific_code(self) -> None:
    response = self.calculate("1/0")
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.json()["code"], "DIVISION_BY_ZERO")
```

4. 每个测试**独立可重复**：`setUp` 中清空数据表，不依赖执行顺序
5. 必须覆盖**正常路径与异常路径**，异常路径要断言具体的错误码
6. 关键行为要有"证据级"断言，例如直接查库确认数据真的落盘：

```python
def test_data_is_really_in_database(self) -> None:
    self.calculate("9+9")
    with get_connection() as connection:
        row = connection.execute(
            "SELECT expression, result FROM calculation_history"
        ).fetchone()
    self.assertEqual(row["result"], "18")
```

7. 使用 `subTest` 组织同一断言的多个输入参数

---

## 10. 注释语言与文件编码

- 源码注释与文档字符串统一使用**简体中文**，便于助教阅读
- 变量名、函数名、类名使用**英文**
- 所有源文件使用 **UTF-8** 编码，不带 BOM
- 仓库通过 `.gitattributes` 强制 `eol=lf`，避免跨平台换行符差异

---

## 11. 自查清单

提交前逐项确认：

- [ ] 所有函数都有类型注解
- [ ] 所有公开模块/类/函数都有 docstring
- [ ] 单行长度不超过 88 字符
- [ ] 导入分为标准库/第三方/本项目三组，使用绝对导入
- [ ] 没有 `eval` / `exec`，没有拼接 SQL
- [ ] 没有裸 `except:`
- [ ] 多行容器都有尾随逗号
- [ ] SQL 只出现在 `repository/` 层
- [ ] 路由函数只做参数解析与响应组装
- [ ] `python -m unittest discover -s tests -t .` 全部通过
