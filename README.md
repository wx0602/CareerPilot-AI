# CareerPilot AI

CareerPilot AI 是一个面向求职训练的全栈项目，包含登录、游客体验、训练场景选择、材料上传、笔试练习、文本面试和报告生成。

## 技术栈

- 前端：Vue 3 + Vite
- 后端：Python 3.11 + FastAPI
- 数据库：SQLite
- 题库与知识层：`knowledge/`
- AI 与评分逻辑：`ai-core/`

## 目录说明

- `frontend/`：前端页面与路由
- `backend/`：FastAPI 接口、数据库、迁移脚本
- `knowledge/`：题库、解析、RAG 相关代码
- `ai-core/`：Agent、Prompt、评分与报告逻辑

## 本地启动前准备

建议环境：

- Node.js 18+
- Python 3.11

首次启动前，需要分别安装前端和后端依赖。

### 1. 安装前端依赖

在仓库根目录执行：

```bash
npm install
```

### 2. 安装后端依赖

Windows PowerShell：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
alembic upgrade head
cd ..
```

macOS / Linux：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
cd ..
```

## 本地启动

### 方式一：从仓库根目录同时启动前后端

这个方式有前置条件，不是开箱即用：

- 根目录必须先执行过 `npm install`
- 后端依赖必须已经安装完成
- 数据库迁移必须已经执行过
- 建议先准备好 `backend/.env`

```bash
npm run dev
```

满足上面的前置条件后，这个命令会同时启动：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`

### 方式二：分别启动

前端：

```bash
npm run dev:frontend
```

后端：

```bash
npm run dev:backend
```

如果 `npm run dev` 不能用，通常不是前端问题，而是上面的前置条件没有满足。最常见的是：

- 根目录没执行过 `npm install`，导致 `concurrently` 不存在
- 后端依赖没装，`uvicorn` / `fastapi` / `sqlalchemy` 不可用
- 没跑过 `alembic upgrade head`
- `backend/.env` 还没创建


## 启动成功后可访问

- 前端页面：`http://127.0.0.1:5173`
- 后端接口健康检查：`http://127.0.0.1:8000/health`
- Swagger 文档：`http://127.0.0.1:8000/docs`

默认演示账号：

- 账号：`demo@careerpilot.local`
- 密码：`Demo123!`

## 常见问题

### 登录、注册、游客进入都失败

优先检查这几项：

1. 后端是否真的启动在 `http://127.0.0.1:8000`
2. `backend/.env` 是否已创建
3. 数据库迁移是否已执行：`alembic upgrade head`
4. 前端和后端是否同时在运行

只启动前端、不启动后端时，登录页无法完成登录，也无法进入主界面。

### 后端启动时报数据库未迁移

进入 `backend/` 目录后执行：

```bash
alembic upgrade head
```

### 根目录启动后端导入失败

当前根目录脚本已经使用：

```bash
python -m uvicorn backend.app.main:app --reload
```

如果你是在 `backend/` 目录内手动启动，则使用：

```bash
uvicorn app.main:app --reload
```
