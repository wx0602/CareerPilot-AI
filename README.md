# CareerPilot AI

CareerPilot AI 是一个面向求职准备与职业能力训练的全栈应用。系统将真实题库、材料解析、多智能体 AI、模拟面试、能力报告和真实岗位搜索串成完整流程，帮助用户从“确定方向”逐步走到“针对岗位训练”。

请访问https://career-pilot-ai-frontend-lyart.vercel.app/

## 当前功能

### 场景选择

- 集中提供企业笔试、文本面试、群体面试、压力面试、路演答辩和职业规划六类场景入口
- 企业笔试可继续选择目标企业与应聘岗位，并根据岗位使用对应题型配比生成专项套题
- 文本面试可结合简历或 JD 展开多轮问答、回答评价和针对性追问
- 群体面试模拟无领导小组讨论；压力面试根据回答动态追问，并支持暂停、停止或降低压力
- 路演答辩结合 PPT、商业计划书或项目介绍，围绕市场价值、商业逻辑、可行性、创新性和表达能力进行质询
- 职业规划提供 MBTI、霍兰德等第三方中文职业测评入口

### 上传简历

- 支持上传简历或职位描述（JD），可选择进入文本面试或数字人面试，也可跳过上传直接开始
- 支持 PDF、DOC、DOCX 和 TXT 文件，单文件不超过 10 MB；当前真实文本解析支持 PDF、DOCX 和 TXT
- 自动提取文本、技能、教育经历、工作经历和项目经历等结构化信息，作为后续面试上下文
- 从路演答辩场景进入时，还可上传 PPTX、PDF、DOC、DOCX 或 TXT 格式的路演 PPT、商业计划书和项目介绍

### 学习计划

- 提供 Java、Python、JavaScript、TypeScript、Vue、浏览器原理、Go、C++、AI / LLM、产品、测试和运维学习模块
- 从 SQLite 真实题库检索题目，按固定配比生成单选、多选、判断和简答练习
- 客观题使用固定逻辑批改，简答题由大模型评分，并输出错题分析、薄弱知识点和学习建议
- 练习过程中可以收藏题目，完成后自动生成对应能力报告

### 岗位推荐

- 可使用简历、最近一次笔试或面试报告，或综合两者生成求职画像
- 求职画像支持编辑目标岗位、期望城市与薪资、学历、工作经验、核心技能、项目经历和薄弱技能
- 搜索实时岗位并与企业官方招聘种子库合并去重；实时源不可用时由本地种子岗位兜底
- 按岗位方向、技能、城市、学历经验、薪资和最近报告表现计算 0～100 匹配分
- 展示推荐理由、匹配技能、缺失技能、改进建议、公开薪资和原始申请链接，并可直接发起针对该岗位的模拟面试

### 我的报告

- 自动保存企业笔试、文本面试、群体面试、压力面试和数字人面试生成的结构化报告
- 展示综合得分、能力维度、得分趋势、优势亮点、待提升项和 AI 建议
- 数字人面试报告额外展示本地非语言表现反馈，该分数不计入综合得分和能力雷达图
- 支持在历史报告间切换查看，并可打印下载或分享当前报告

### 收藏题库

- 集中查看笔试练习中收藏的题目及收藏日期
- 支持按题型筛选，并可按题干或题目编号搜索
- 展开后可查看题目详情、选项、正确答案和解析，也可以取消收藏
- 未收藏题目时可从页面直接返回学习计划开始笔试练习

### 数字人展示

- 通过数字人面试官朗读题目，支持文字作答和浏览器语音输入
- 提供本地真人摄像头预览、摄像头切换以及麦克风和朗读控制
- 在浏览器本地分析动作与姿态；分析不可用时不会阻断面试流程，画面也不会自动上传或保存
- 完成至少一轮问答后可结束面试并生成能力报告

### 我的

- 支持注册、登录、游客体验、登录状态保持和退出登录
- 展示完成练习、累计答题、收藏题目、能力报告数量和最近学习时间
- 正式账号可设置昵称、头像风格、目标岗位和求职阶段，并同步保存成长记录
- 提供“我的报告”“收藏题库”和“学习计划”的快捷入口；游客可体验核心流程，注册后可跨设备长期保存数据

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
| 数据库 | SQLite、PostgreSQL |
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

- 岗位薪资完全依赖 API 原始字段；缺失时不会用大模型估算。
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
