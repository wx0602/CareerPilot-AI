# 第一阶段 API 接口约定

本文件由 B 主导维护。当前 B 侧接口均已实现；C/D 的真实函数尚未接入时可通过 `PROVIDER_MODE=stub` 使用固定开发数据联调。

## 通用约定

- 基础地址：`http://127.0.0.1:8000`
- Swagger：`GET /docs`
- 除登录、游客和健康检查外，请求头必须包含 `Authorization: Bearer <access_token>`。
- 成功响应直接返回业务 JSON，不增加额外 `data` 包装。
- 模式值：`job`（求职）、`technical`（技术）、`pitch`（路演）。第一阶段完整验收 `technical`。
- 时间使用 ISO 8601，服务端按 UTC 保存。
- 错误格式：

```json
{
  "detail": {
    "code": "guest_session_limit",
    "message": "游客只能创建一个训练会话"
  }
}
```

常用状态码：`401` 未登录或令牌过期、`403` 越权、`404` 不存在、`409` 流程冲突、`413` 文件过大、`415` 文件无效、`422` 参数错误、`502/503` 外部能力返回无效或尚未接入。

## 认证

### `POST /api/auth/login`

```json
{
  "account": "demo@careerpilot.local",
  "password": "Demo123!",
  "remember_me": false
}
```

```json
{
  "access_token": "只在本次响应返回的原始令牌",
  "token_type": "bearer",
  "expires_at": "2026-07-15T02:00:00Z",
  "user": {
    "user_id": "uuid",
    "account": "demo@careerpilot.local",
    "is_guest": false
  }
}
```

普通令牌有效24小时，`remember_me=true` 时30天。

### `POST /api/auth/guest`

无请求体。返回与登录相同的令牌结构，`user_id/account` 为 `null`，`is_guest=true`，有效期2小时。游客令牌只能创建一个训练会话。

### `POST /api/auth/logout`

撤销当前令牌，成功返回 `204 No Content`。

## 训练会话

### `POST /api/training-sessions`

```json
{
  "mode": "technical",
  "position": "后端开发工程师",
  "company": "示例企业"
}
```

返回 `201`：

```json
{
  "session_id": "uuid",
  "mode": "technical",
  "position": "后端开发工程师",
  "company": "示例企业",
  "status": "created",
  "created_at": "2026-07-14T02:00:00Z"
}
```

后续材料、笔试、面试和报告都必须使用该 `session_id`。

## 材料上传

### `POST /api/materials/upload`

使用 `multipart/form-data`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `session_id` | string | 当前训练会话 |
| `material_type` | `resume \| jd` | 第一阶段材料类型 |
| `file` | file | PDF、DOC、DOCX、TXT，最大10MB |

返回材料编号、原文件名、MIME、大小和 `pending | parsed | failed` 解析状态。文件使用 UUID 名称保存，文件内容与扩展名不匹配时返回 `415`。

## 企业笔试

### `POST /api/exams/generate`

```json
{
  "session_id": "uuid",
  "position": "后端开发工程师",
  "company": "示例企业",
  "difficulty": "medium",
  "question_count": 10
}
```

返回 `ExamPaperResponse`：`exam_id`、`session_id`、`title`、`questions`。题目只包含 `question_id`、`question_type`、`content`、`options`，绝不包含答案和解析。同一会话重复生成时返回原试卷。

### `POST /api/exams/submit`

```json
{
  "session_id": "uuid",
  "exam_id": "uuid",
  "answers": [
    {"question_id": "q1", "answer": "B"},
    {"question_id": "q2", "answer": ["A", "C"]}
  ]
}
```

返回 `ExamResultResponse`：`exam_id`、`score`、`question_results`、`weaknesses`、`suggestions`。相同答案重试返回已保存结果；提交不同答案返回 `409 exam_already_submitted`。

### `GET /api/exams/{exam_id}/result`

读取已保存的批改和错题分析；未提交时返回 `404`。

## 文本面试

### `POST /api/interviews/message`

首次获取问题：

```json
{"session_id": "uuid"}
```

提交回答：

```json
{
  "session_id": "uuid",
  "question_id": "uuid",
  "answer": "我的回答内容"
}
```

响应：

```json
{
  "interview_id": "uuid",
  "evaluation": null,
  "next_question": {
    "question_id": "uuid",
    "question": "面试问题"
  },
  "is_followup": false
}
```

回答后 `evaluation` 包含总分、分项评分、优缺点及追问标记。接口只接受最新未回答问题；相同回答可安全重试，修改已回答内容或乱序回答返回 `409`。

## 报告

### `POST /api/reports/generate`

```json
{
  "session_id": "uuid",
  "nonverbal_score": null
}
```

B 从数据库加载笔试和面试数据后构造 D 的 `ReportRequest`，前端不能传入或覆盖内容评分。普通 `job` 数字人面试可额外提交经过明确 Schema 校验的本地辅助字段 `nonverbal_score`；其状态仅允许 `complete | insufficient_data`，五个维度分数限制为 `0～100`，且不参与 `overall_score`。至少完成笔试或一轮面试，否则返回 `409 no_training_result`。

响应遵循公共 `ReportResponse`：`session_id`、`mode`、`overall_score`、`dimension_scores`、`strengths`、`weaknesses`、`suggestions`、`charts`、`summary`，以及可选的 `nonverbal_score`。非语言结果只随新报告写入现有 `reports.payload_json`；已有报告仍直接返回原值，不补写或覆盖。

### `GET /api/reports/{session_id}`

读取已生成报告。同一训练会话重复生成时返回已保存报告。

## C/D 函数边界

C 提供：

```text
parse_material(path, material_type) -> list[ContextChunk]
```

D 提供：

```text
generate_exam(GenerateExamRequest) -> (ExamPaperResponse, list[QuestionBankItem])
grade_exam(ExamSubmission, list[QuestionBankItem]) -> ExamResultResponse
generate_question(GenerateQuestionRequest) -> QuestionResponse
evaluate_answer(EvaluateAnswerRequest) -> EvaluationResponse
generate_report(ReportRequest) -> ReportResponse
```

其中 `QuestionBankItem` 含答案，只允许 B 在数据库私有保存，不得进入公开试卷响应。
