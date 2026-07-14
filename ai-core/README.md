# ai-core：LangChain / LangGraph 多智能体 AI 工作区

本目录只包含 D 组负责的 AI 能力实现，公共数据模型严格复用根目录 `models.py`。

## 架构说明

当前 ai-core 使用 LangChain 调用真实 DeepSeek API，并使用 LangGraph 编排多智能体流程。外部调用仍然使用原有公共函数：

- `generate_exam`
- `grade_exam`
- `generate_question`
- `evaluate_answer`
- `generate_report`

这些函数保持返回格式兼容，内部统一进入 LangGraph workflow。

## Agent

| Agent | 职责 |
| --- | --- |
| `SupervisorAgent` | 读取共享 State 中的 `task_type`，识别任务并通过条件边路由 |
| `ExamAgent` | 组卷、客观题批改、简答题评分、错题分析 |
| `InterviewAgent` | 根据 `job`、`technical`、`pitch` 模式生成问题 |
| `EvaluationAgent` | 对面试回答进行多维度评分，并按需生成追问 |
| `ReportAgent` | 生成综合报告、建议和图表 JSON 数据 |

LangGraph 入口在 `agents/workflow.py`：

```text
SupervisorAgent
  ├─ generate_exam / grade_exam ──> ExamAgent ──> END
  ├─ generate_question ───────────> InterviewAgent ──> END
  ├─ evaluate_answer ─────────────> EvaluationAgent ──> END
  └─ generate_report ─────────────> ReportAgent ──> END
```

共享 State 字段包括：

- `task_type`
- `request`
- `question_bank`
- `expected_question_ids`
- `next_agent`
- `response`

## Skill

6 个 Skill 统一定义在 `skills/definitions.py`：

| Skill | 用途 |
| --- | --- |
| `written_exam` | 笔试组卷、错题分析和薄弱点总结 |
| `short_answer_grading` | 简答题大模型评分 |
| `job_interview` | HR 求职面试 |
| `technical_interview` | 技术面试 |
| `pitch_interview` | 路演答辩 |
| `report_generation` | 综合报告生成 |

Prompt 放在 `prompts/`：

- `written_exam.md`
- `short_answer_grading.md`
- `job_interview.md`
- `technical_interview.md`
- `pitch_interview.md`
- `report_generation.md`
- `answer_evaluation.md`：EvaluationAgent 专用评分 Prompt

## 环境变量

`ai-core/.env` 需要包含：

```ini
LLM_API_KEY=...
LLM_BASE_URL=...
LLM_MODEL=...
```

代码只读取这些配置，不打印、不修改密钥。`LLM_BASE_URL` 支持：

- `https://api.deepseek.com`
- `https://api.deepseek.com/v1`
- `https://api.deepseek.com/v1/chat/completions`

## 安装依赖

只安装 ai-core 需要的依赖：

```powershell
pip install -r ai-core/requirements.txt
```

## 调用方法

由于目录名 `ai-core` 带连字符，建议调用方把 `ai-core` 加入 `PYTHONPATH` 后导入：

```python
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root / "ai-core"))

from agents import (
    evaluate_answer,
    generate_exam,
    generate_question,
    generate_report,
    grade_exam,
)
```

### 生成笔试

```python
from models import GenerateExamRequest

paper = generate_exam(
    GenerateExamRequest(
        session_id="s1",
        position="Java 后端工程师",
        company="示例公司",
        difficulty="medium",
        question_count=10,
    ),
    question_bank,
)
```

返回 `ExamPaperResponse`，题目中不会包含 `answer` 或 `explanation`。

### 批改笔试

```python
result = grade_exam(
    submission,
    question_bank,
    expected_question_ids=[q.question_id for q in paper.questions],
)
```

- 单选、多选、判断题由 Python 固定逻辑批改。
- 简答题调用 DeepSeek，并通过 `short_answer_grading` Skill 输出合法 JSON。
- JSON 解析或 Pydantic 校验失败时最多重试两次。

### 生成面试问题

```python
question = generate_question(request)
```

`InterviewAgent` 会根据 `mode` 选择：

- `job` -> `job_interview`
- `technical` -> `technical_interview`
- `pitch` -> `pitch_interview`

### 评价回答

```python
evaluation = evaluate_answer(request)
```

返回 `EvaluationResponse`，包含总分、分项评分、优点、不足、是否追问和追问问题。

### 生成报告

```python
report = generate_report(request)
```

返回 `ReportResponse`，包含综合总结、建议和 `charts` 图表 JSON 数据。报告只生成数据，不生成图片。

## 约束

- 所有用户可见内容均为中文。
- 公共输入输出模型使用根目录 `models.py`。
- DeepSeek 输出统一走 JSON 解析和 Pydantic 校验。
- 固定计算逻辑仍使用普通 Python，例如客观题批改、分数计算和薄弱点汇总。
- 不使用模拟模型。
