# B 工作区：后端与数据库接口

本目录归 B 负责，当前只提供 FastAPI 项目骨架，不包含真实接口逻辑、数据库读写或文件处理逻辑。

## 建议职责

- 登录、游客模式、用户历史记录接口
- 上传简历、JD、项目介绍、商业计划书、PPT 的接口
- 笔试、批改、错题分析、面试、报告接口
- SQLite 表结构与迁移说明
- 与 C、D 的函数调用边界

## 目录说明

| 目录 | 用途 |
| --- | --- |
| `app/api/routes/` | 按业务模块拆分路由 |
| `app/core/` | 配置、启动参数、安全相关占位 |
| `app/db/` | SQLite 连接、表结构、迁移占位 |
| `app/models/` | 数据库模型占位 |
| `app/schemas/` | Pydantic 请求和响应结构占位 |
| `app/services/` | 调用 C、D 工作区的服务层占位 |
| `uploads/` | 本地上传文件暂存目录 |

## 本地后端命令规划

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
