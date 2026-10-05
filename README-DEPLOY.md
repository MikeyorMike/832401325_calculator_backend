# 部署与验收说明（务必先读这一份）

> 本文档说明如何把项目部署到公网，让助教能够访问验收。
> 作业要求：**前后端都必须可访问**，前端项目与后端项目分别放在**两个 GitHub 仓库**。

---

## 0. 时间提醒

| 事项 | 时间 |
| --- | --- |
| 作业截止 | **2026-10-07 23:59** |
| 博客需审核 | 发布后可能显示 404，**必须提前发布** |
| 逾期提交 | 截止后 2 天内提交得**实际分数的 50%** |
| 超期未交 | 截止 2 天后 **0 分** |

> 当前系统时间已是 **2026-10-05**，请**今天就完成部署并在今晚发布博客**，
> 给审核留出缓冲时间。博客链接先提交到作业页面，等审核通过即可。

---

## 1. 总览：要交付什么

| 交付物 | 位置 | 谁来准备 |
| --- | --- | --- |
| 后端 GitHub 仓库 | GitHub 新建仓库 | 你（按第 2 节操作） |
| 前端 GitHub 仓库 | GitHub 新建仓库 | 你（按第 2 节操作） |
| 后端公网地址 | Render 自动生成 | 你（按第 3 节操作） |
| 前端公网地址 | Netlify 自动生成 | 你（按第 4 节操作） |
| 博客（含 10+ 截图） | CSDN / 博客园等 | 你（按第 6 节操作） |
| PSP 表 | 博客内 | 已提供模板，见 `docs/PSP表.md` |

---

## 2. 第一步：把代码推送到两个 GitHub 仓库

### 2.1 准备：安装 Git

如果本机没有 Git，先到 <https://git-scm.com/download/win> 下载安装。
安装后在终端执行 `git --version` 应能看到版本号。

### 2.2 创建两个空仓库

登录 GitHub → 右上角 `+` → **New repository**，创建两个仓库：

| 仓库名 | 类型 | 建议设置 |
| --- | --- | --- |
| `832401325_calculator_backend` | Public | **不要**勾选 Add README（避免冲突） |
| `832401325_calculator_frontend` | Public | **不要**勾选 Add README |

> 助教需要能访问仓库，因此必须选 **Public**。

### 2.3 推送后端仓库

打开终端，执行（把 `你的用户名` 换成 GitHub 用户名）：

```powershell
cd C:\Users\Mikey\Documents\deepseek-harness\default-workspace\832401325_calculator_backend

git init
git add .
git commit -m "feat: 前后端分离计算器后端（FastAPI + SQLite）"
git branch -M main
git remote add origin https://github.com/你的用户名/832401325_calculator_backend.git
git push -u origin main
```

### 2.4 推送前端仓库

```powershell
cd C:\Users\Mikey\Documents\deepseek-harness\default-workspace\832401325_calculator_frontend

git init
git add .
git commit -m "feat: 前后端分离计算器前端（原生 HTML/CSS/JS）"
git branch -M main
git remote add origin https://github.com/你的用户名/832401325_calculator_frontend.git
git push -u origin main
```

> **推不上去怎么办？**
> - 提示 `Authentication failed`：GitHub 已不支持密码推送，需要创建 **Personal Access Token**
>   （Settings → Developer settings → Personal access tokens → Tokens (classic) → 勾选 `repo`），
>   推送时密码位置填这个 token。
> - 提示 `Permission denied`：确认仓库地址里的用户名写对了。

---

## 3. 第二步：部署后端到 Render

Render 免费、无需信用卡，是本次部署的首选。

### 3.1 注册

访问 <https://render.com> → **Get Started** → 用 **GitHub 账号**登录（免邮箱验证）。

### 3.2 创建 Web Service

1. 控制台点击 **New +** → **Web Service**
2. 选择 **Build and deploy from a Git repository** → Next
3. 连接你的 `832401325_calculator_backend` 仓库
4. 填写配置：

| 配置项 | 填什么 |
| --- | --- |
| **Name** | `calculator-backend`（决定域名，可自定义） |
| **Region** | `Singapore`（离国内最近） |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn src.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | `Free` |

5. 展开 **Advanced** → **Add Environment Variable**，添加：

| Key | Value |
| --- | --- |
| `PYTHON_VERSION` | `3.12.0` |
| `RELOAD` | `false` |
| `CORS_ALLOW_ORIGINS` | 先填 `*`，前端部署好后再改成前端域名 |

6. 点击 **Create Web Service**，等待构建（首次约 3~5 分钟）

### 3.3 验证后端

构建完成后，Render 会给出地址，形如：

```
https://calculator-backend-xxxx.onrender.com
```

浏览器访问 `<该地址>/api/health`，应返回：

```json
{"success":true,"status":"ok","app":"Calculator Backend","version":"1.0.0"}
```

再访问 `<该地址>/docs` 应能看到 Swagger 接口文档。

> ⚠️ **记下这个地址，第 4 步要用。**

### 3.4 免费实例的休眠问题（重要）

Render 免费实例 **15 分钟无请求会休眠**，再次访问需要 30~50 秒冷启动。

**应对办法**：在博客里明确写一句提示，例如：

> 本项目后端部署在 Render 免费实例上，若首次访问较慢（约 30~50 秒），
> 是在冷启动，请稍等片刻。建议先访问
> [健康检查接口](https://你的后端地址/api/health) 唤醒服务，再打开前端页面。

**更好办法**：用免费的定时任务每 10 分钟 ping 一次健康检查接口，保持服务常醒。
例如 <https://uptimerobot.com> 免费版即可配置 HTTP 监控。
这属于「部署踩坑与解决」的真实素材，**建议写进博客第 8 节**。

---

## 4. 第三步：部署前端到 Netlify

前端是纯静态文件（HTML/CSS/JS），不需要构建，部署极简。

### 4.1 修改后端地址

打开 `832401325_calculator_frontend/src/js/config.js`，把 `apiBaseUrl` 改成第 3.3 步拿到的后端地址：

```javascript
window.CALCULATOR_CONFIG = {
  apiBaseUrl: 'https://calculator-backend-xxxx.onrender.com',   // ← 改成你的
  requestTimeoutMs: 60000,     // 冷启动较慢，超时放宽到 60 秒
  historyPageSize: 10,
  searchDebounceMs: 320,
  verboseLog: true
};
```

> **为什么超时要放宽？** Render 冷启动需要 30~50 秒，
> 默认 15 秒会在冷启动时误报「请求超时」。

改完**提交并推送**：

```powershell
cd C:\Users\Mikey\Documents\deepseek-harness\default-workspace\832401325_calculator_frontend
git add .
git commit -m "chore: 配置线上后端地址"
git push
```

### 4.2 部署到 Netlify

1. 访问 <https://app.netlify.com> → 用 **GitHub 账号**登录
2. 点击 **Add new site** → **Import an existing project**
3. 选择 **GitHub** → 授权 → 选中 `832401325_calculator_frontend` 仓库
4. 填写构建设置：

| 配置项 | 填什么 |
| --- | --- |
| **Branch to deploy** | `main` |
| **Base directory** | **留空**（⚠️ 切勿填 `src`，会与 `netlify.toml` 的 `publish = "src"` 叠加成 `src/src`，报错 `Deploy directory 'src/src' does not exist`） |
| **Build command** | 留空 |
| **Publish directory** | `src` 或留空（`netlify.toml` 中已指定 `publish = "src"`） |

> 仓库里的 `netlify.toml` 已声明发布目录为 `src`，并配了一条 `[[redirects]]`
> 把未知路径回退到 `index.html`。**界面 Base directory 留空即可**，不要重复指定。

5. 点击 **Deploy site**，等待约 30 秒
6. 得到地址形如 `https://random-name-123.netlify.app`

### 4.3 验证前端

1. 打开 Netlify 给的地址
2. 页面顶部状态徽标应显示 **「后端已连接 · v1.0.0」**（绿色圆点）
3. 输入 `(1+2)*3` 点击「=」，应显示 `9`
4. 右侧历史列表应出现这条记录
5. 用 `F12` 打开控制台，Network 面板能看到对后端的请求，**证明前后端确实分离通信**

### 4.4 回填 CORS 白名单（收尾，但建议做）

回到 Render → 你的服务 → **Environment** → 把 `CORS_ALLOW_ORIGINS` 改为：

```
https://random-name-123.netlify.app
```

保存后服务会自动重新部署。这样做比 `*` 更规范，博客里可以作为一个「安全加固」的点写出来。

> 如果重新部署后前端连不上，先检查这个地址是否与 Netlify 地址**完全一致**（含 `https://`，不含结尾 `/`）。

### 4.5 可选：替换为易记的域名

Netlify → Site configuration → **Change site name**，可改成例如
`832401325-calculator`，地址即变为 `https://832401325-calculator.netlify.app`，更好记也更好写进博客。

---

## 5. 第四步：部署后的自查清单

逐项确认，全部打勾才去写博客：

- [ ] 后端 `/api/health` 公网可访问，返回 `status: ok`
- [ ] 后端 `/docs` 公网可访问，能看到 10 个接口
- [ ] 前端公网地址能打开，状态徽标显示「后端已连接」
- [ ] `12+8` 能算出 `20`
- [ ] `1+2*3` 能算出 `7`（优先级正确）
- [ ] `(1+2)*3` 能算出 `9`（括号正确）
- [ ] `-5+8` 能算出 `3`（一元负号）
- [ ] `0.1+0.2` 能算出 `0.3`（小数精度）
- [ ] `1/0` 显示错误提示且不崩溃
- [ ] `1++*2` 显示「表达式非法」
- [ ] 计算后刷新页面，**历史记录仍在**（证明存在后端数据库）
- [ ] 删除某条历史后刷新，**该条确实消失**（证明数据库真删了）
- [ ] 点击「进制」标签，`255` 十进制转二进制得到 `11111111`
- [ ] 点击「单位」标签，`100` 摄氏度转华氏度得到 `212`
- [ ] 点击「科学」标签，`144` 开平方得到 `12`
- [ ] 两个 GitHub 仓库都是 Public，且都能看到 `README.md` 和 `codestyle.md`
- [ ] 前端 Netlify 地址与后端 Render 地址都能在**别人的电脑/手机**上打开

> **最后一条很重要**：用手机 4G（不要连 Wi-Fi）打开前端地址验证一次，
> 确保不是只有你自己能访问。

---

## 6. 第五步：写博客并提交

### 6.1 博客必备要素（对照评分表）

| 评分项 | 分值 | 对应要求 | 状态 |
| --- | --- | --- | --- |
| Markdown 格式正确 | 15' | 使用 Markdown 标题层级、代码块、表格 | 见 `docs/博客初稿.md` |
| 目录可跳转 | 15' | 每个标题都要有锚点链接 | 初稿已带 |
| GitHub 仓库链接 | 15' | 前端、后端各一个，放在**文章开头** | 需你填入 |
| 代码规范链接 | 15' | 前端、后端 `codestyle.md` 各一个 | 需你填入 |
| PSP 表 | 15' | 计划时间 + 实际时间两列 | 见 `docs/PSP表.md` |
| 部署/访问信息 | 15' | 前端可访问地址 + 后端地址 | 需你填入 |
| 截图 ≥ 10 张 | 15' | 每张配文字说明 | 见 `docs/截图清单.md` |
| 需求分析 | 15' | 功能清单、非功能需求 | 初稿已写 |
| 功能结构图 | 15' | 树状结构图 | 初稿已写 |
| 前端/后端/API/数据库设计 | 15' | 四类设计 | 初稿已写 |
| 关键代码讲解 | 15' | 解析器、API、数据库操作 | 初稿已写 |

### 6.2 发布流程

1. 把 `docs/博客初稿.md` 的内容粘贴到 CSDN 编辑器（或博客园）
2. 参考 `docs/截图清单.md` 逐张截图并**替换占位符**
3. 填入 4 个链接：前端仓库、后端仓库、前端 codestyle、后端 codestyle
4. 填入 2 个地址：前端访问地址、后端地址
5. 按 `docs/PSP表.md` 填入计划时间与**真实实际时间**
6. 预览确认目录能跳转
7. **立即发布**（不要等到截止日）
8. 在作业页面提交博客链接

> **为什么必须提前发布？** 作业原文写明：博客发布后需要审核，
> 审核期间链接会显示 404。提前发布可以等审核通过，避免影响提交。

### 6.3 截图的正确做法

- **必须是你自己跑起来的真实页面**，不要用示意图或网图
- 推荐工具：Windows 自带 `Win + Shift + S`（区域截图）、
  [ShareX](https://getsharex.com/)（可录 GIF）
- 关键操作建议录 **GIF**（如「计算 → 历史出现 → 删除 → 刷新仍在」的完整流程），
  比静态图更有说服力
- 每张图下面**必须写一句说明**（评分要求「accompanied by a brief text description」）

---

## 7. 本地重新运行（答辩/演示时用）

如果助教要求现场演示，或网络不稳需要本地跑：

### 7.1 启动后端

```powershell
cd C:\Users\Mikey\Documents\deepseek-harness\default-workspace\832401325_calculator_backend

# 首次需要建虚拟环境并装依赖
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 启动
python run.py
```

终端出现 `Uvicorn running on http://127.0.0.1:8000` 即成功。

### 7.2 启动前端

前端是纯静态文件，**不能直接双击 `index.html`**（浏览器对 `file://` 协议的
跨域限制会导致请求失败）。需要用本地服务器：

**方式一：用 Python 起静态服务器**（推荐，无需装东西）

```powershell
cd C:\Users\Mikey\Documents\deepseek-harness\default-workspace\832401325_calculator_frontend\src
python -m http.server 5500
```

然后浏览器打开 <http://127.0.0.1:5500>

**方式二：VS Code 的 Live Server 插件**
右键 `index.html` → **Open with Live Server**

### 7.3 确认本地后端地址

本地演示前，把 `src/js/config.js` 的 `apiBaseUrl` 改回：

```javascript
apiBaseUrl: 'http://127.0.0.1:8000',
requestTimeoutMs: 15000
```

> 演示结束后记得改回线上地址并推送，或在本地用另一个分支。

---

## 8. 部署踩坑备查

写博客第 8 节「个人历程」时，以下几个坑都是真实且值得写的素材：

| 现象 | 原因 | 解决办法 |
| --- | --- | --- |
| 前端提示「无法连接后端服务」 | 浏览器 CORS 拦截 | 后端设置 `CORS_ALLOW_ORIGINS` 为前端域名 |
| 首次访问要等 30~50 秒 | Render 免费实例冷启动 | 用 UptimeRobot 定时 ping；前端超时放宽到 60 秒 |
| 前端在本地直接双击打不开 | `file://` 协议下 fetch 被限制 | 用 `python -m http.server` 起本地服务器 |
| 重新部署后历史记录清空 | Render 免费实例磁盘是临时的 | 作业演示够用；要持久化需挂载 Disk 或换 PostgreSQL |
| Render 构建失败提示找不到 pydantic-core | 平台默认 Python 3.14，该版本轮子不全 | 设置环境变量 `PYTHON_VERSION=3.12.0` |
| 推送 GitHub 提示认证失败 | GitHub 不再支持密码推送 | 用 Personal Access Token 代替密码 |
| 删除记录后刷新又出现了 | 只在前端移除了 DOM 节点，没调后端 | 必须调 `DELETE /api/history/{id}` 并重新查询 |

---

## 9. 需要你手动填写的占位符清单

代码与文档中所有 `<待填写>` 都是需要你替换的位置：

| 文件 | 位置 | 填什么 |
| --- | --- | --- |
| `832401325_calculator_backend/README.md` | 文末「相关链接」 | 前端仓库地址、前端 codestyle 地址、博客地址 |
| `832401325_calculator_frontend/README.md` | 文末「相关链接」 | 后端仓库地址、后端 codestyle 地址 |
| `832401325_calculator_frontend/src/js/config.js` | `apiBaseUrl` | Render 后端地址 |
| `docs/博客初稿.md` | 开头链接区 | 4 个链接 + 2 个访问地址 |
| `docs/博客初稿.md` | 各 `【截图 N】` | 替换为真实截图 |
| `docs/PSP表.md` | 实际时间列 | 你的真实耗时 |

用搜索功能全局搜 `<待填写>` 可以快速定位。
