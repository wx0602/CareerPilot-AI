# CareerPilot AI

CareerPilot AI 是一个面向求职准备与职业能力训练的全栈应用。系统将真实题库、材料解析、多智能体 AI、模拟面试、能力报告和真实岗位搜索串成完整流程，帮助用户从“确定方向”逐步走到“针对岗位训练”。

## 当前功能

### 账号与个人中心

- 注册、登录、记住登录状态和游客体验
- Bearer Token 鉴权与退出登录
- “我的”页面支持昵称、头像风格、目标岗位和求职阶段设置
- 展示完成练习、累计答题、收藏题目、能力报告和最近学习时间
- 游客可体验核心流程，正式账号可长期保存数据

### 学习计划与题库练习

- Java、Python、JavaScript、TypeScript、Vue、浏览器原理、Go、C++、AI / LLM、产品、测试和运维学习模块
- 固定题型配比生成练习：单选、多选、判断和简答
- 从 SQLite 真实题库检索题目，支持岗位、企业、难度、题型和知识点筛选
- 客观题固定逻辑批改，简答题使用大模型评分
- 错题分析、薄弱知识点和学习建议
- 题目收藏与取消收藏

### 企业笔试

- 按企业和应聘岗位选择专项套题
- 支持阿里巴巴、京东、美团、小红书等前端已配置企业入口
- 不同岗位使用独立题型配比
- 交卷后直接生成专项能力报告，笔试与面试流程相互独立

### AI 模拟面试

- 文本面试：结合简历或 JD 生成问题、评价回答并进行针对性追问
- 群体面试：与多名 AI 候选人完成文字版无领导小组讨论
- 压力面试：根据回答质量动态追问，支持暂停、停止和降低压力
- 路演答辩：围绕市场价值、商业逻辑、可行性、创新性和表达能力进行质询
- 岗位定向面试：将真实岗位 JD、岗位技能和用户画像传入现有面试模块

### 材料上传与解析

- 上传简历、JD、项目介绍、商业计划书和路演 PPT
- 上传接口校验 PDF、DOC、DOCX、TXT 和 PPTX；当前真实文本解析支持 PDF、DOCX、TXT 和 PPTX
- 提取文本、技能、教育经历、工作经历和项目经历等结构化信息
- 材料解析结果可用于面试上下文和求职画像生成

### 岗位推荐

- 画像来源支持：简历、最近一次笔试或面试报告、简历与报告综合
- AI 生成可编辑求职画像，包括目标岗位、期望城市、薪资、学历、经验、技能、项目和薄弱项
- 后端直连 OpenWeb Ninja 官方 JSearch `search-v2`，并与企业官方招聘种子库合并去重，API Key 不进入浏览器
- 严格筛选不足时依次放宽薪资和经验、城市与岗位同义词；实时源失败时返回种子库 Top 5
- 按技能、岗位方向、城市、学历经验、薪资和最近报告表现计算 0～100 匹配分
- 展示推荐理由、已匹配技能、缺失技能、改进建议、真实薪资和原始申请链接
- API 未提供薪资时统一显示“薪资未公开”，大模型不生成岗位事实或具体薪资
- 已适配 cursor 分页结构，当前版本只取第一页

### 报告、职业规划与数字人展示

- 笔试、文本面试、群体面试和压力面试可生成结构化报告
- 报告包含综合分、维度分、优势、薄弱项、建议和图表数据
- “我的报告”支持历史报告列表与详情查看
- 职业规划提供 MBTI、霍兰德等第三方中文测评入口
- 数字人展示页支持浏览器语音朗读、语音输入和本地摄像头预览

## 系统架构

```text
Vue 3 / Vite
      │
      ▼
FastAPI API ─────────────── SQLAlchemy / Alembic
      │                           │
      ├─ Knowledge Provider       ├─ SQLite（本地）
      │    ├─ SQLite 题库          └─ PostgreSQL（生产）
      │    ├─ 材料解析
      │    └─ 关键词 / 可选 Chroma 检索
      │
      ├─ AI Provider
      │    └─ LangGraph Supervisor
      │         ├─ Exam Agent
      │         ├─ Interview / Evaluation Agent
      │         ├─ Group / Stress Interview Agent
      │         ├─ Report Agent
      │         └─ Job Recommendation Agent
      │
      └─ OpenWeb Ninja JSearch
           └─ 真实岗位、公司、薪资和申请链接
```

公共 Pydantic 数据模型集中在根目录 `models.py`。后端通过 Provider 层复用 `knowledge/` 和 `ai-core/`，避免在 API 路由中重复实现题库检索、材料解析或 AI 编排。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、Vue Router、Vite 5 |
| 后端 | Python 3.12、FastAPI、Pydantic 2 |
| 数据库 | SQLite、PostgreSQL、SQLAlchemy 2、Alembic |
| AI | LangChain、LangGraph、OpenAI-compatible LLM |
| 知识层 | SQLite 题库、规则解析、可选 Chroma |
| 文件解析 | pypdf、python-docx、python-pptx |
| 岗位数据 | OpenWeb Ninja JSearch API |
| 测试 | pytest、Starlette TestClient |
| 部署 | Vercel 前后端双项目 |

## 项目结构

```text
CareerPilot-AI/
├─ frontend/                 # Vue 页面、路由、组件和 API Client
├─ backend/                  # FastAPI、数据库实体、服务、迁移和测试
│  ├─ app/api/routes/        # 认证、材料、笔试、面试、报告、岗位推荐
│  ├─ app/services/          # Provider、岗位推荐和普通业务服务
│  ├─ migrations/versions/   # Alembic 数据库迁移
│  └─ tests/                 # 后端自动化测试
├─ knowledge/                # 题库、材料解析、RAG 和知识层测试
├─ ai-core/                  # Agent、LangGraph 工作流、Prompt 和 LLM Client
├─ docs/                     # API 契约与部署说明
├─ models.py                 # 前后端业务使用的公共 Python 数据模型
├─ app.py                    # Vercel Python 后端入口
├─ package.json              # 根目录开发与构建命令
└─ vercel.json               # 后端 Vercel 配置
```

## 本地运行

### 环境要求

- Node.js 22.x
- Python 3.12.x
- npm

### 1. 安装依赖

在仓库根目录执行：

```powershell
npm install

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
python -m pip install -r ai-core\requirements.txt
python -m pip install pypdf python-docx python-pptx
```

macOS / Linux 激活虚拟环境：

```bash
source .venv/bin/activate
```

Chroma 是可选能力。需要本地向量索引时再安装：

```powershell
python -m pip install -r knowledge\requirements.txt
```

### 2. 配置后端环境变量

复制本地模板：

```powershell
Copy-Item backend\.env.example backend\.env
```

`backend/.env` 主要配置：

```ini
APP_ENV=development
DATABASE_URL=sqlite:///./careerpilot.db
PROVIDER_MODE=real
JSEARCH_API_KEY=YOUR_OPENWEB_NINJA_JSEARCH_KEY
JSEARCH_TIMEOUT_SECONDS=10
```

真实 AI Provider 还需要创建 `ai-core/.env`：

```ini
LLM_API_KEY=YOUR_LLM_API_KEY
LLM_BASE_URL=https://your-openai-compatible-provider.example/v1
LLM_MODEL=YOUR_MODEL_NAME
```

本地接口联调或自动测试可将 `PROVIDER_MODE` 设置为 `stub`。岗位搜索仍然需要有效的 `JSEARCH_API_KEY`。

所有密钥只能配置在后端或部署平台环境变量中。不要给 `LLM_API_KEY`、`JSEARCH_API_KEY` 添加 `VITE_` 前缀，否则会被 Vite 打包到浏览器代码。

### 3. 执行数据库迁移

```powershell
npm run db:migrate
```

也可以在 `backend/` 目录执行：

```powershell
python -m alembic -c alembic.ini upgrade head
```

### 4. 启动前后端

同时启动：

```powershell
npm run dev
```

分别启动：

```powershell
npm run dev:frontend
npm run dev:backend
```

启动后访问：

- 前端：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/health`
- Swagger：`http://127.0.0.1:8000/docs`

默认本地演示账号：

```text
账号：demo@careerpilot.local
密码：Demo123!
```

演示账号只适合本地开发，部署前必须修改 `DEMO_PASSWORD`。

## 常用命令

```powershell
# 前后端开发
npm run dev

# 前端生产构建
npm run build

# 数据库升级
npm run db:migrate

# 全量后端与知识层测试
python -m pytest backend\tests knowledge\tests -q

# 只测试岗位推荐
python -m pytest backend\tests\test_job_recommendations.py -q
```

## 主要接口

除登录、注册、游客入口和健康检查外，业务接口均需要：

```http
Authorization: Bearer <access_token>
```

| 模块 | 接口 |
| --- | --- |
| 认证 | `POST /api/auth/register`、`POST /api/auth/login`、`POST /api/auth/guest`、`POST /api/auth/logout` |
| 我的 | `GET /api/auth/me`、`PATCH /api/auth/me` |
| 会话 | `POST /api/training-sessions`、`PATCH /api/training-sessions/{session_id}` |
| 材料 | `POST /api/materials/upload` |
| 笔试 | `POST /api/exams/generate`、`POST /api/exams/submit`、`GET /api/exams/{exam_id}/result` |
| 文本面试 | `POST /api/interviews/message` |
| 群体/压力面试 | `/api/simulations/*` |
| 报告 | `POST /api/reports/generate`、`GET /api/reports`、`GET /api/reports/{session_id}` |
| 收藏 | `GET /api/favorites`、`POST /api/favorites`、`DELETE /api/favorites/{question_id}` |
| 岗位画像 | `POST /api/job-recommendations/profile` |
| 岗位搜索 | `POST /api/job-recommendations/search` |
| 岗位面试 | `POST /api/job-recommendations/interview` |

完整请求与响应字段见 [API 接口约定](docs/API_CONTRACT.md)。

## 部署

当前生产方案使用两个 Vercel 项目：

1. 后端项目使用仓库根目录，通过根目录 `app.py` 和 `vercel.json` 部署 FastAPI。
2. 前端项目的 Root Directory 设置为 `frontend`。
3. 生产数据库必须使用 PostgreSQL，不能使用 SQLite。
4. 前端配置 `VITE_API_BASE_URL=https://YOUR_BACKEND_DOMAIN`。
5. 后端配置数据库、CORS、LLM 和 JSearch 环境变量后执行一次 Alembic 迁移。

详细步骤见 [Vercel 部署说明](docs/VERCEL_DEPLOYMENT.md)。

## 当前限制

- OpenWeb Ninja JSearch 对中国大陆城市的岗位覆盖可能较少；实时源无结果或失败时会使用本地企业官方岗位种子库兜底。
- JSearch 当前只读取 `search-v2` 第一页，尚未在前端提供继续加载 cursor 的交互。
- 岗位薪资完全依赖 API 原始字段；缺失时不会用大模型估算。
- 扫描版 PDF 暂未接入 OCR，需要上传包含可复制文本的文件。
- 旧版二进制 DOC 可以通过上传校验，但当前解析器尚不能提取其正文，建议转换为 DOCX。
- 数字人页面当前是浏览器语音、摄像头预览和 AI 对话界面，不是实时生成的视频数字人。
- 职业规划中的测评由第三方网站提供，部分平台可能包含可选付费服务。
- Vercel 文件系统是临时存储，生产环境的大文件长期保存需要接入 Vercel Blob、S3 等对象存储。
- 内置题库用于产品流程和训练验证，生产使用前仍应继续扩充并进行人工审核。

## 进一步文档

- [后端说明](backend/README.md)
- [AI 多智能体说明](ai-core/README.md)
- [题库与知识层说明](knowledge/README.md)
- [API 接口约定](docs/API_CONTRACT.md)
- [Vercel 部署说明](docs/VERCEL_DEPLOYMENT.md)
