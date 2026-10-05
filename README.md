# Calculator Backend —— 前后端分离计算器系统（后端）

> 本项目实现计算器系统的**后端服务**，负责表达式校验、解析、计算、异常处理与历史记录持久化。

---

## 目录

- [1. 项目简介](#1-项目简介)
- [2. 技术栈](#2-技术栈)
- [3. 运行环境](#3-运行环境)
- [4. 安装步骤](#4-安装步骤)
- [5. 启动方式](#5-启动方式)
- [6. 配置说明](#6-配置说明)
- [7. 数据库初始化](#7-数据库初始化)
- [8. 前后端连接方式](#8-前后端连接方式)
- [9. API 接口文档](#9-api-接口文档)
- [10. 项目结构](#10-项目结构)
- [11. 测试](#11-测试)
- [12. 部署](#12-部署)
- [13. 设计要点](#13-设计要点)
- [14. 常见问题](#14-常见问题)

---

## 1. 项目简介

本项目是「前后端分离计算器系统」的**后端部分**。

核心职责：

| 职责 | 说明 |
| --- | --- |
| 接收计算请求 | 接收前端发来的表达式字符串 |
| 输入校验 | 空值、长度上限、字符白名单三重校验 |
| 表达式解析 | 手写词法分析 + 递归下降语法分析（**不使用 eval/exec**） |
| 执行计算 | 使用 `Decimal` 高精度十进制运算 |
| 异常处理 | 除零、非法表达式、括号不匹配、结果溢出 |
| 历史持久化 | 计算记录写入 SQLite 数据库 |
| 历史读删 | 分页查询、关键字搜索、删除单条、清空全部 |
| 标准化响应 | 统一 JSON 结构与 HTTP 状态码 |

**重要原则**：所有计算都在后端完成。前端只负责把表达式发过来、把结果展示出去，不参与任何算术运算。

---

## 2. 技术栈

| 层次 | 选型 | 选择理由 |
| --- | --- | --- |
| 语言 | Python 3.11+ | 语法简洁，标准库自带 `Decimal` 与 `sqlite3` |
| Web 框架 | FastAPI 0.115 | 自带请求校验与 OpenAPI 文档，便于助教直接查看接口 |
| 数据校验 | Pydantic 2.x | 声明式模型定义，非法请求自动返回 422 |
| 数据库 | SQLite 3 | 零配置、单文件，无需安装数据库服务，便于部署 |
| 数据访问 | 原生 `sqlite3` + 参数化 SQL | 表结构简单，手写 SQL 更能体现数据库设计思路 |
| ASGI 服务器 | Uvicorn | 轻量，一行命令启动 |
| 测试 | `unittest`（标准库） | 无需额外依赖，`python -m unittest` 直接运行 |

> **为什么不用 ORM？** 本项目只需一张表，引入 ORM 会掩盖 SQL 逻辑，
> 反而让「数据库设计」这一评分点不易展示。使用原生 SQL 配合参数化查询，
> 既保证安全（防 SQL 注入），又保留了可读性。

---

## 3. 运行环境

| 项目 | 要求 |
| --- | --- |
| 操作系统 | Windows / macOS / Linux 均可 |
| Python | **3.11 或更高**（推荐 3.11 ~ 3.13） |
| 数据库 | 无需额外安装，SQLite 由 Python 标准库提供 |
| 内存 | 64 MB 以上即可 |
| 端口 | 默认 8000（可通过 `PORT` 环境变量修改） |

> **Python 3.14 用户注意**：`pydantic-core` 在 3.14 上仅部分版本提供预编译轮子。
> 若在 3.14 上安装失败，建议改用 3.12 或 3.13。

检查 Python 版本：

```bash
python --version
```

---

## 4. 安装步骤

### 4.1 获取代码

```bash
git clone <本仓库地址>
cd 832401325_calculator_backend
```

### 4.2 创建虚拟环境（推荐）

**Windows（PowerShell）**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4.3 安装依赖

```bash
pip install -r requirements.txt
```

依赖清单（`requirements.txt`）：

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
```

若需要运行测试，额外安装：

```bash
pip install httpx
```

---

## 5. 启动方式

### 方式一：使用启动脚本（推荐）

```bash
python run.py
```

### 方式二：直接使用 uvicorn

```bash
uvicorn src.main:app --reload --port 8000
```

### 方式三：指定端口

```bash
# Windows PowerShell
$env:PORT="9000"; python run.py

# macOS / Linux
PORT=9000 python run.py
```

启动成功后终端会输出：

```
数据库已就绪：.../data/calculator.db
允许的跨域来源：['*']
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 访问地址

| 地址 | 说明 |
| --- | --- |
| <http://127.0.0.1:8000> | 服务信息（JSON） |
| <http://127.0.0.1:8000/docs> | **Swagger UI 交互式接口文档** |
| <http://127.0.0.1:8000/redoc> | ReDoc 风格的接口文档 |
| <http://127.0.0.1:8000/api/health> | 健康检查 |

> **验证服务是否正常**：浏览器打开 <http://127.0.0.1:8000/api/health>，
> 若返回 `{"success": true, "status": "ok", ...}` 说明后端已正常运行。

---

## 6. 配置说明

所有配置通过**环境变量**注入，无需修改代码。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PORT` | `8000` | 服务监听端口 |
| `RELOAD` | `true` | 是否开启热重载（生产环境建议设为 `false`） |
| `DATABASE_PATH` | `./data/calculator.db` | SQLite 数据库文件路径 |
| `CORS_ALLOW_ORIGINS` | `*` | 允许跨域的前端来源，多个用英文逗号分隔 |
| `MAX_EXPRESSION_LENGTH` | `200` | 表达式最大长度 |
| `DECIMAL_PRECISION` | `28` | 计算精度（有效数字位数） |
| `MAX_RESULT_MAGNITUDE` | `1e100` | 结果绝对值上限，超过则报溢出 |

**生产环境建议配置**（把前端域名加进白名单，而不是放行所有来源）：

```bash
CORS_ALLOW_ORIGINS=https://your-frontend.netlify.app
RELOAD=false
```

---

## 7. 数据库初始化

**无需手动初始化**：应用启动时会自动建表（幂等操作，重复启动不会出错）。

也可以手动执行辅助脚本：

```bash
# 建表
python scripts/manage_db.py init

# 查看最近 10 条历史
python scripts/manage_db.py show

# 清空全部历史
python scripts/manage_db.py clear
```

### 表结构

```sql
CREATE TABLE IF NOT EXISTS calculation_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,  -- 主键，自增
    expression    TEXT    NOT NULL,                   -- 计算表达式
    result        TEXT    NOT NULL,                   -- 计算结果（字符串保精度）
    created_at    TEXT    NOT NULL,                   -- 计算时间（ISO 8601 带时区）
    is_favorite   INTEGER NOT NULL DEFAULT 0,         -- 是否收藏（扩展功能）
    is_extended   INTEGER NOT NULL DEFAULT 0          -- 是否扩展功能计算
);

-- 索引：加速「按时间倒序分页」与「表达式搜索」
CREATE INDEX idx_history_created_at ON calculation_history (created_at DESC);
CREATE INDEX idx_history_expression ON calculation_history (expression);
CREATE INDEX idx_history_favorite   ON calculation_history (is_favorite);
```

**字段设计说明**

| 字段 | 类型选择理由 |
| --- | --- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT`，作为删除操作的唯一标识 |
| `expression` | 存归一化后的表达式（如 `1+2*3`），便于搜索 |
| `result` | 用 `TEXT` 而非 `REAL`，避免浮点精度丢失（`0.1+0.2` 可精确存为 `0.3`） |
| `created_at` | 存 ISO 8601 字符串（带时区偏移），便于排序与前端本地化显示 |
| `is_favorite` | 扩展功能「收藏记录」所需 |
| `is_extended` | 区分基础计算与扩展功能计算，便于分类展示 |

**为什么不做用户表？** 作业未要求登录体系，单用户场景下引入用户表只会增加复杂度。
若要扩展多用户，只需增加 `user_id` 外键与 `users` 表即可。

---

## 8. 前后端连接方式

### 8.1 通信协议

```
前端（浏览器 / 小程序 / App）
      │
      │  HTTP + JSON
      │  POST /api/calculate   { "expression": "(1+2)*3" }
      ▼
后端（FastAPI）
      │
      │  SQL（参数化）
      ▼
SQLite 数据库
```

### 8.2 前端需要配置的地方

前端项目中的 `src/js/config.js` 指定后端地址：

```javascript
window.CALCULATOR_CONFIG = {
  apiBaseUrl: 'http://127.0.0.1:8000',   // 本地开发
  // apiBaseUrl: 'https://your-backend.onrender.com',  // 部署后
  requestTimeoutMs: 15000
};
```

### 8.3 跨域（CORS）说明

前后端分离部署时，前端域名与后端域名不同，浏览器会拦截跨域请求。
后端已通过 `CORSMiddleware` 显式放行，配置项为 `CORS_ALLOW_ORIGINS`。

- 本地开发：默认 `*`（放行所有来源），方便调试
- 线上部署：建议改成具体的前端域名

**验证 CORS 是否生效**：

```bash
curl -i -X OPTIONS http://127.0.0.1:8000/api/calculate \
  -H "Origin: http://localhost:5500" \
  -H "Access-Control-Request-Method: POST"
```

响应头中应包含 `access-control-allow-origin`。

---

## 9. API 接口文档

所有接口以 `/api` 为前缀，请求与响应均为 `application/json`。

### 9.1 接口总览

| 方法 | 路径 | 功能 | 对应作业要求 |
| --- | --- | --- | --- |
| `GET` | `/api/health` | 健康检查 | 部署验证 |
| `POST` | `/api/calculate` | 计算表达式并落库 | 功能一、功能二 |
| `GET` | `/api/history` | 分页查询历史 | 功能三 |
| `GET` | `/api/history/{id}` | 查询单条历史 | 功能三 |
| `DELETE` | `/api/history/{id}` | 删除指定历史 | **功能四** |
| `DELETE` | `/api/history` | 清空全部历史 | 扩展功能 |
| `PATCH` | `/api/history/{id}/favorite` | 切换收藏状态 | 扩展功能 |
| `GET` | `/api/statistics` | 计算统计 | 扩展功能 |
| `POST` | `/api/extended` | 科学计算/进制转换/单位换算 | 扩展功能 |
| `GET` | `/api/extended/capabilities` | 扩展功能能力清单 | 扩展功能 |

### 9.2 计算表达式

`POST /api/calculate`

**请求体**

```json
{
  "expression": "(1+2)*3",
  "is_extended": false
}
```

**成功响应** `201 Created`

```json
{
  "success": true,
  "expression": "(1+2)*3",
  "normalized": "(1+2)*3",
  "result": "9",
  "record": {
    "id": 1,
    "expression": "(1+2)*3",
    "result": "9",
    "created_at": "2026-10-05T19:38:12+08:00",
    "is_favorite": false,
    "is_extended": false
  }
}
```

> `result` 是**字符串**而非数字，这样可以精确保留任意精度的小数结果。

**失败响应** `400 Bad Request`

```json
{
  "success": false,
  "code": "DIVISION_BY_ZERO",
  "message": "除数不能为零",
  "detail": null
}
```

**错误码对照表**

| `code` | 状态码 | 触发条件 |
| --- | --- | --- |
| `INVALID_EXPRESSION` | 400 | 语法错误、非法字符、括号不匹配 |
| `DIVISION_BY_ZERO` | 400 | 除数为零 |
| `EXPRESSION_TOO_LONG` | 400 | 表达式超过长度上限 |
| `RESULT_OVERFLOW` | 400 | 结果超出可表示范围 |
| `VALIDATION_ERROR` | 422 | 请求体结构错误（缺字段、类型错误） |
| `RECORD_NOT_FOUND` | 404 | 指定的历史记录不存在 |
| `INTERNAL_ERROR` | 500 | 服务端未预期异常 |

### 9.3 查询历史

`GET /api/history?page=1&page_size=10&keyword=1%2B2&favorites_only=false`

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `page` | int | `1` | 页码，从 1 开始 |
| `page_size` | int | `20` | 每页条数，1~100 |
| `keyword` | string | 无 | 关键字，匹配表达式或结果 |
| `favorites_only` | bool | `false` | 是否仅返回收藏记录 |

**响应** `200 OK`

```json
{
  "success": true,
  "items": [
    {
      "id": 3,
      "expression": "(2+3)*4",
      "result": "20",
      "created_at": "2026-10-05T19:40:00+08:00",
      "is_favorite": false,
      "is_extended": false
    }
  ],
  "page": 1,
  "page_size": 10,
  "total": 3,
  "total_pages": 1
}
```

### 9.4 删除历史记录

`DELETE /api/history/{id}`

**响应** `200 OK`

```json
{
  "success": true,
  "message": "已删除历史记录 id=3",
  "deleted_id": 3,
  "deleted_count": null
}
```

记录不存在时返回 `404`。该操作会**真实删除数据库中的行**，删除后前端重新查询即可看到最新状态。

### 9.5 扩展功能

`POST /api/extended`

**科学计算**

```json
{ "type": "scientific", "function": "sqrt", "operands": ["144"] }
```

可用函数：`sqrt` `square` `cube` `power` `reciprocal` `abs` `log10` `ln` `log2`
`exp` `factorial` `sin` `cos` `tan` `ceil` `floor` `round`
（三角函数使用**角度制**）

**进制转换**

```json
{ "type": "base", "value": "255", "from_base": 10, "to_base": 2 }
```

支持 2 / 8 / 10 / 16 进制互转。

**单位换算**

```json
{ "type": "unit", "category": "temperature", "value": "100", "from_unit": "c", "to_unit": "f" }
```

支持类别：`length`（长度）、`mass`（质量）、`area`（面积）、`temperature`（温度）。

---

## 10. 项目结构

```
832401325_calculator_backend/
├── src/
│   ├── __init__.py
│   ├── main.py                     # 应用入口：FastAPI 实例、CORS、异常处理、路由注册
│   ├── api/                        # 【接口层】只做参数解析与响应组装
│   │   ├── __init__.py
│   │   ├── routes.py               # 所有 HTTP 路由定义
│   │   └── schemas.py              # Pydantic 请求/响应模型（接口契约）
│   ├── service/                    # 【业务层】核心逻辑，不含 SQL
│   │   ├── __init__.py
│   │   ├── calculator.py           # ★ 表达式解析与求值引擎（本项目核心）
│   │   ├── history_service.py      # 历史业务编排：计算并落库、查询、删除
│   │   └── extended_service.py     # 扩展功能：科学计算/进制转换/单位换算
│   ├── repository/                 # 【数据访问层】所有 SQL 集中于此
│   │   ├── __init__.py
│   │   └── history_repository.py   # 历史记录 CRUD
│   └── core/                       # 【基础设施层】
│       ├── __init__.py
│       ├── config.py               # 环境变量配置
│       ├── database.py             # SQLite 连接管理与建表
│       └── exceptions.py           # 统一异常体系
├── tests/                          # 测试代码（111 个用例）
│   ├── __init__.py
│   ├── test_calculator.py          # 表达式引擎单元测试（47）
│   ├── test_api.py                 # API 集成测试（40）
│   └── test_extended.py            # 扩展功能测试（24）
├── scripts/
│   ├── manage_db.py                # 数据库辅助管理脚本
│   └── e2e_check.py                # 端到端验证脚本（对真实服务发请求）
├── data/                           # SQLite 数据文件（已加入 .gitignore）
├── requirements.txt                # 依赖清单
├── run.py                          # 本地启动脚本
├── codestyle.md                    # 代码规范文档
├── README.md                       # 本文件
└── render.yaml                     # Render 部署配置
```

**分层依赖方向**：`api → service → repository → core`，单向依赖，不允许反向调用。

---

## 11. 测试

### 运行全部测试

```bash
python -m unittest discover -s tests -t . -v
```

预期输出：

```
Ran 111 tests in 0.9s
OK
```

### 分模块测试

```bash
python -m unittest tests.test_calculator -v   # 表达式引擎（47 个）
python -m unittest tests.test_api -v          # API 接口（40 个）
python -m unittest tests.test_extended -v     # 扩展功能（24 个）
```

### 测试覆盖内容

| 测试文件 | 覆盖点 |
| --- | --- |
| `test_calculator.py` | 四则运算、运算优先级、左结合性、括号嵌套、一元正负、小数精度、非法表达式、除零、溢出、**代码注入防护**、全角符号归一化 |
| `test_api.py` | 四个必需功能的完整 HTTP 链路、分页、搜索、**直接查库验证持久化**、错误码与状态码、CORS |
| `test_extended.py` | 科学函数、进制转换、单位换算（含温度偏移量）、参数校验 |

### 端到端验证（针对已启动的服务）

先启动后端，再执行：

```bash
python scripts/e2e_check.py http://127.0.0.1:8000
```

该脚本会发起**真实网络请求**（不经过 TestClient），验证 44 项断言，
包括 CORS 预检、Swagger 文档可访问性等部署相关行为。

### 手工验证示例

```bash
# 基础计算
curl -X POST http://127.0.0.1:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d "{\"expression\": \"(1+2)*3\"}"

# 除零处理
curl -X POST http://127.0.0.1:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d "{\"expression\": \"1/0\"}"

# 查询历史
curl http://127.0.0.1:8000/api/history

# 删除记录
curl -X DELETE http://127.0.0.1:8000/api/history/1
```

---

## 12. 部署

### 12.1 部署到 Render（推荐，免费且无需信用卡）

1. 把本仓库推送到 GitHub
2. 登录 <https://render.com>，选择 **New → Web Service**
3. 连接你的 GitHub 仓库
4. 填写配置：

| 配置项 | 值 |
| --- | --- |
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn src.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | `Free` |

5. 添加环境变量：

| 变量名 | 值 |
| --- | --- |
| `CORS_ALLOW_ORIGINS` | `https://你的前端域名.netlify.app` |
| `RELOAD` | `false` |
| `PYTHON_VERSION` | `3.12.0` |

6. 点击 **Create Web Service**，等待部署完成
7. 访问 `https://你的服务名.onrender.com/api/health` 确认部署成功

> ⚠️ **免费实例的注意事项**
> - 服务在 15 分钟无请求后会休眠，下次请求需要约 30~50 秒冷启动。
>   助教验收前建议先访问一次 `/api/health` 把服务唤醒。
> - 免费实例的磁盘是临时的，**重新部署会导致 SQLite 数据被清空**。
>   若需要持久化，可改用 Render 的 Disk 功能（付费）或换成 PostgreSQL。
>   对于本作业演示，临时存储足够；如需长期保留，请参见 `README-DEPLOY.md`。

### 12.2 使用 Docker 部署

仓库根目录提供 `Dockerfile`：

```bash
docker build -t calculator-backend .
docker run -d -p 8000:8000 -e CORS_ALLOW_ORIGINS="*" calculator-backend
```

### 12.3 部署到自己的服务器

```bash
# 安装依赖
pip install -r requirements.txt

# 后台启动
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# 确认启动
curl http://127.0.0.1:8000/api/health
```

生产环境建议用 `systemd` 或 `supervisor` 托管进程，并在前面加 Nginx 反向代理以支持 HTTPS。

---

## 13. 设计要点

### 13.1 为什么不使用 eval/exec？

作业明确禁止。`eval` 会把用户输入当作**程序代码**执行，攻击者可以提交：

```
__import__('os').system('rm -rf /')
```

本项目采用「词法分析 + 递归下降语法分析」，用户输入只可能被解释为**数字和四则运算符**，
从原理上杜绝了代码执行。测试中还包含 `test_no_eval_in_source`，
静态检查核心模块源码中不出现 `eval(` / `exec(`。

### 13.2 文法设计（优先级如何体现）

```
expression := term (('+' | '-') term)*       ← 加减，优先级最低
term       := unary (('*' | '/') unary)*     ← 乘除，优先级更高
unary      := ('+' | '-') unary | primary    ← 一元正负号
primary    := NUMBER | '(' expression ')'    ← 数字与括号
```

优先级由**文法层次**天然编码：越靠下的规则结合越紧。
因此 `1+2*3` 会被解析成 `1+(2*3)` 而不是 `(1+2)*3`；
一元正负号放在 `unary` 层，所以 `3*-2` 和 `-5+8` 都能正确解析。

### 13.3 为什么用 Decimal 而不是 float？

`float` 是二进制浮点，无法精确表示 `0.1`：

```python
>>> 0.1 + 0.2
0.30000000000000004     # float
>>> Decimal("0.1") + Decimal("0.2")
Decimal('0.3')          # Decimal
```

计算器出现 `0.30000000000000004` 会严重影响体验，因此采用 `Decimal`，
配合 28 位有效数字的上下文精度。

### 13.4 为什么结果存成字符串？

数据库字段与 API 响应都用字符串保存结果，原因：

1. 避免 JSON 数字在超大/超小数值时退化为科学计数法或丢失精度
2. SQLite 的 `REAL` 是 8 字节浮点，存不下高精度 Decimal
3. 前端只需原样展示，不需要再做数值运算

### 13.5 分层架构的价值

| 层次 | 只关心 | 不关心 |
| --- | --- | --- |
| `api` | HTTP、参数校验、状态码 | 怎么算、怎么存 |
| `service` | 业务规则、计算、异常语义 | HTTP、SQL |
| `repository` | SQL 与数据映射 | 业务规则 |
| `core` | 配置、连接、异常定义 | 上层逻辑 |

好处：换数据库只改 `repository`；加接口只改 `api`；改算法只改 `service`。
测试也能分层进行（单元测试直接测 `calculator`，不必启动 HTTP 服务）。

---

## 14. 常见问题

**Q1：启动报 `ModuleNotFoundError: No module named 'fastapi'`**
→ 依赖未安装或虚拟环境未激活。执行 `pip install -r requirements.txt`，
并确认终端提示符前有 `(.venv)`。

**Q2：前端页面提示「无法连接后端服务」**
→ 依次检查：
1. 后端是否已启动（访问 <http://127.0.0.1:8000/api/health>）
2. 前端 `config.js` 里的 `apiBaseUrl` 是否与后端地址一致
3. 后端 `CORS_ALLOW_ORIGINS` 是否放行了前端来源
4. 浏览器 F12 控制台的 Network 面板是否有 CORS 报错

**Q3：端口 8000 被占用**
→ 换端口启动：`PORT=9000 python run.py`，同时更新前端 `apiBaseUrl`。

**Q4：历史记录突然变空了**
→ 可能执行了「清空历史」，或（在云端）服务重新部署导致临时磁盘重置。
本地开发时确认 `DATABASE_PATH` 指向的是同一个数据库文件。

**Q5：计算结果和 Windows 计算器不一致**
→ 本实现使用十进制精确运算，Windows 计算器部分场景使用二进制浮点。
例如 `0.1+0.2` 本实现返回 `0.3`（更符合数学预期）。

**Q6：想改用 MySQL / PostgreSQL**
→ 只需修改 `src/core/database.py` 的连接部分与 `src/repository/history_repository.py`
中的 SQL 占位符风格（SQLite 用 `?`，MySQL 用 `%s`），业务层无需改动。

---

## 附：代码规范

本项目的代码规范见 [codestyle.md](./codestyle.md)，主要参考：

- [PEP 8 – Style Guide for Python Code](https://peps.python.org/0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

---

## 附：相关链接

| 内容 | 地址 |
| --- | --- |
| 前端仓库 | `<待填写>` |
| 前端代码规范 | `<待填写>` |
| 后端代码规范 | [codestyle.md](./codestyle.md) |
| 部署与验收说明 | [README-DEPLOY.md](./README-DEPLOY.md) |
| 作业博客 | `<待填写>` |
