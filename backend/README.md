# B 工作区：后端与数据库接口

本目录由 B 负责。第一阶段的 FastAPI 接口、SQLite 数据库、Alembic 迁移、C/D 适配层和开发桩已经实现；未修改 A、C、D 的工作区代码。

## 当前进度（2026-07-24）

| 里程碑 | 状态 | 说明 |
| --- | --- | --- |
| 配置、数据库、迁移 | 已完成 | Alembic `20260724_0005`；SQLite 外键、WAL、忙等待和查询索引已启用 |
| 登录、游客、训练会话 | 已完成 | 数据库令牌、密码哈希、游客单会话限制 |
| 简历/JD 上传 | B 侧已完成 | 真实 C 解析函数待接入，当前可使用开发桩 |
| 笔试、批改、错题分析 | B 侧已完成 | 真实 D 函数待接入，私有答案不会返回前端 |
| 文本面试、追问、报告 | B 侧已完成 | 真实 D 函数待接入，当前可使用开发桩 |
| 日志与故障定位 | 已完成 | 请求 ID、结构化滚动日志、慢请求/慢查询和数据库异常降级 |
| 自动化测试 | 已完成 | 最新 `main` 后端 65 项通过 |
| Python 3.11 复验 | 已完成 | Python 3.11.9 下迁移、测试和服务启动均通过 |
| A/C/D 最终联调 | 待完成 | 等待 C/D 真实函数后再交 A 接口联调 |

## 本地运行

第一阶段使用本地 SQLite 和本地上传目录验收，不以 Vercel 持久化为目标。

PowerShell：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

`requirements-dev.txt` 会同时安装后端、`ai-core` 和 `knowledge` 的仓库既有依赖。没有配置大模型密钥时，将 `backend/.env` 中的 `PROVIDER_MODE` 改为 `stub` 即可先跑通笔试、数字人面试和报告流程。使用 `PROVIDER_MODE=real` 时，还必须创建 `ai-core/.env`：

```ini
LLM_API_KEY=你的密钥
LLM_BASE_URL=OpenAI兼容接口地址
LLM_MODEL=模型名称
```

AI 依赖或配置不可用时，后端会返回结构化的 `503 ai_provider_unavailable`，不会再产生未处理异常堆栈。

Linux/macOS：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

服务启动后访问：

- Swagger：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`
- 默认演示账号：`demo@careerpilot.local`
- 默认演示密码：`Demo123!`

演示账号仅用于本地开发，可通过 `.env` 修改。密码以 Argon2 哈希保存在数据库中。

## 数据库与日志配置

本地 SQLite 连接默认启用外键约束、WAL、`NORMAL` 同步模式和 5 秒忙等待；请求异常时 SQLAlchemy 会话自动回滚。`/health` 会返回数据库方言、当前 Alembic 版本，以及 SQLite 的外键和日志模式。

应用日志默认同时输出到控制台和 `backend/logs/app.log`。文件采用 JSON Lines 格式并按大小轮转；每个响应都携带 `X-Request-ID`，可用它关联一整次请求。日志只记录方法、路径、状态码、耗时和错误栈，不记录请求正文、密码、Bearer Token、上传文件内容或 SQL 参数。

常用配置：

```ini
DATABASE_BUSY_TIMEOUT_MS=5000
SLOW_QUERY_MS=500
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_DIR=./logs
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=5
SLOW_REQUEST_MS=1000
```

Vercel 等无状态环境应使用 `LOG_TO_FILE=false`，由平台采集控制台日志。

## 测试与迁移

```powershell
python -m pytest -q --cov=app --cov-report=term
alembic current
alembic downgrade base
alembic upgrade head
```

最近验证结果：项目 `.venv` 使用 Python 3.11；65 项后端测试全部通过，空 SQLite 数据库可升级到 `20260724_0005 (head)`，健康检查可返回数据库状态。

## 接口概览

- 认证：登录、游客令牌、退出。
- 训练会话：创建 `job | technical | pitch` 模式会话。
- 材料：上传 `resume | jd`，支持 PDF、DOC、DOCX、TXT，最大 10MB。
- 笔试：生成、提交、自动批改、错题分析、结果读取。
- 面试：首题、回答评分、追问、下一题和幂等重试。
- 报告：根据数据库中的笔试与面试结果生成和读取报告。

详细请求和响应见 [`../docs/API_CONTRACT.md`](../docs/API_CONTRACT.md)，数据库结构见 [`../docs/DATABASE_SCHEMA.md`](../docs/DATABASE_SCHEMA.md)。

## C/D 集成边界

B 只维护 `app/services/providers.py` 中的适配协议：

- C：`parse_material(path, material_type) -> list[ContextChunk]`
- D：`generate_exam`、`grade_exam`、`generate_question`、`evaluate_answer`、`generate_report`

`.env` 默认使用 `PROVIDER_MODE=real`，笔试会从 `knowledge/question_bank/questions.sqlite3` 检索真实题目，并在所选难度题量不足时从同一学习模块的其他难度补足。`PROVIDER_MODE=stub` 仅用于后端自动化测试和接口联调，不应作为本地体验配置。

## 当前未完成项

- 接入 C 的真实简历/JD 解析结果。
- 接入 D 的真实组卷、评分、追问和报告函数。
- 将 OpenAPI 契约与演示账号交给 A 完成前端联调。
