# CareerPilot AI

以企业笔试题库和用户材料为知识基础，通过 RAG 提供检索依据，通过 Skill 定义笔试、面试和路演场景规则，通过多 Agent 完成组卷、批改、追问、评分和报告生成，最后用数字人完成拟人化交互展示，形成一个面向求职与创业训练的智能实训平台

## 技术栈规划

- 前端：Vue 3 + Vite
- 后端：Python 3.11 + FastAPI
- 知识库：LangChain + Chroma
- 数据库：SQLite
- 部署：Vercel 优先部署前端演示壳子

## 目录分工

| 目录 | 负责人 | 工作范围 |
| --- | --- | --- |
| `frontend/` | A | 前端页面、数字人展示、交互壳子 |
| `backend/` | B | FastAPI 接口、数据库、上传与历史记录接口 |
| `knowledge/` | C | 题库、RAG、文档解析、Chroma 数据 |
| `ai-core/` | D | Skill、Agent、Prompt、评分和报告 JSON |


## 本地运行前端

```bash
npm install
npm run dev
```
