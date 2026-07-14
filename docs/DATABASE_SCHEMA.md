# 第一阶段数据库结构

数据库由 B 维护，使用 SQLAlchemy 2.x、SQLite 和 Alembic。当前迁移版本为 `20260714_0001`。

## 表结构

| 表 | 用途 | 关键字段与约束 |
| --- | --- | --- |
| `users` | 登录用户 | `account` 唯一，密码只保存 Argon2 哈希 |
| `auth_tokens` | 登录/游客令牌 | 只保存 SHA-256 令牌哈希，记录过期和撤销时间 |
| `training_sessions` | 一次完整训练 | 保存所有者、创建令牌、`mode`、岗位、企业和状态 |
| `materials` | 简历/JD 文件 | 保存安全路径、文件元数据、解析状态和上下文 JSON |
| `exams` | 试卷 | 每个训练会话最多一份，保存标题、难度和状态 |
| `exam_questions` | 试卷题目快照 | 分离公开题目 JSON 与私有评分 JSON，题号在试卷内唯一 |
| `exam_submissions` | 笔试提交与结果 | 每份试卷最多一次，保存答案哈希、答案和评分结果 JSON |
| `interviews` | 文本面试 | 每个训练会话最多一次，保存模式和状态 |
| `interview_turns` | 面试问答轮次 | 轮次和问题编号在面试内唯一，保存回答和评价 JSON |
| `reports` | 综合报告 | 每个训练会话最多一份，保存完整报告 JSON 快照 |

## 关系与所有权

```text
users ──< auth_tokens
users ──< training_sessions >── auth_tokens
training_sessions ──< materials
training_sessions ──1 exams ──< exam_questions
exams ──1 exam_submissions
training_sessions ──1 interviews ──< interview_turns
training_sessions ──1 reports
```

- 登录用户的资源通过 `owner_user_id` 校验。
- 游客资源绑定创建它的 `auth_token`，其他游客令牌不能访问。
- 游客单次体验限制在服务层执行：一个游客令牌只能创建一个训练会话。
- UUID 字符串作为业务主键；时间统一按 UTC 写入。
- AI/RAG 输出使用 JSON 快照，避免外部模型升级后旧记录无法读取。

## 数据安全

- 原始访问令牌不会写入数据库，数据库只保存 SHA-256 哈希。
- 试卷公开题目与正确答案分列保存，API 只读取 `public_payload`。
- 上传文件使用 UUID 文件名，原文件名只作为显示元数据。
- SQLite 文件、数据库文件和实际上传文件均已加入 `.gitignore`。

## 迁移命令

在 `backend` 目录和虚拟环境中执行：

```powershell
alembic current
alembic upgrade head
alembic downgrade base
```

首次启动必须先运行 `alembic upgrade head`。应用不会在启动时绕过迁移自动建表；若数据库尚未迁移，会提示执行迁移命令。

## 第二阶段扩展原则

历史记录接口直接查询现有训练会话、试卷、面试和报告表；ASR/TTS 数据如需持久化，应新增迁移，不直接修改已发布迁移文件。
