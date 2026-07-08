# API 接口约定占位

本文件由 B 主导维护，A、C、D 共同确认字段。当前只列接口边界，不实现逻辑。

## 第一阶段接口

| 模块 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 登录 | `POST` | `/api/auth/login` | 登录并返回用户状态 |
| 游客模式 | `POST` | `/api/auth/guest` | 创建一次性体验会话 |
| 材料上传 | `POST` | `/api/materials/upload` | 上传简历、JD 等材料 |
| 生成笔试 | `POST` | `/api/exams/generate` | 按企业、岗位、难度生成题目 |
| 提交笔试 | `POST` | `/api/exams/submit` | 提交答案并返回批改结果 |
| 文本面试 | `POST` | `/api/interviews/message` | 获取提问或追问 |
| 生成报告 | `POST` | `/api/reports/generate` | 生成综合报告 JSON |

## mode 字段

| mode | 场景 |
| --- | --- |
| `job` | 求职面试 |
| `tech` | 技术面试 |
| `pitch` | 路演答辩 |

## 集成方向

1. A 先使用 `shared/mock-data/` 假数据完成页面。
2. B 先按本文件返回固定结构。
3. C 向 D 提供检索结果。
4. D 向 B 提供问题、评分和报告 JSON。
