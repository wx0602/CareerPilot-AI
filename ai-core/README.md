# D 工作区：Agent、Skill、Prompt、评分报告

本目录归 D 负责，当前只提供 AI 能力的组织框架和 JSON 约定，不包含真实模型调用、评分逻辑或 Prompt 实现。

## 建议职责

- 定义求职面试、技术面试、路演答辩三种模式的 Prompt
- 定义 Skill 和 Agent 的输入输出边界
- 输出 AI 问题、追问、评分、报告 JSON
- 将 C 的 RAG 结果转化为可用于面试和报告的上下文

## 目录说明

| 目录 | 用途 |
| --- | --- |
| `skills/` | 场景 Skill 定义 |
| `agents/` | 组卷、批改、追问、评分、报告 Agent 占位 |
| `prompts/` | 三种模式 Prompt 占位 |
| `scoring/` | 评分维度和报告生成占位 |
| `report_schema/` | 报告 JSON 示例和字段约定 |
