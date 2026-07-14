# C 工作区：题库、RAG、文档解析

本目录提供 CareerPilot AI 的知识数据层，由 C 维护。当前版本已经包含可运行的题库校验与导入、SQLite 存储、Chroma 可选向量索引和题库关键词检索；简历/JD/项目介绍/商业计划书/路演 PPT 的解析与材料检索目前为接口模板，仍需继续完善和验证。

公共数据契约以仓库根目录 `models.py` 为唯一标准：题库对外使用 `QuestionBankItem`，RAG 召回片段对外使用 `ContextChunk`。企业、岗位、难度和来源仅作为 C 的内部检索元数据保存。

## 已完成内容

- 题库字段校验、文本清洗、题号/题干去重和错误记录
- 题库幂等导入 SQLite，可选同步写入 Chroma
- 按企业、岗位、难度、题型、知识点检索题目
- 提供 TXT、Markdown、CSV、JSON、DOCX、PDF、PPTX 的基础解析模板
- 提供简历与 JD 规则提取模板，当前不作为正式检索能力交付
- 提供材料分块、索引及 `search_materials()` 接口模板，后续仍需完善召回效果
- 为 B/D 提供稳定的 `KnowledgeService` Python 接口
- 所有交付给 D 的题目和上下文均通过根目录 Pydantic 公共模型校验
- 提供24道原创跨岗位种子题，覆盖通用、Java、Python、前端、测试、数据/AI、运维和产品运营

## 目录说明

| 目录 | 用途 |
| --- | --- |
| `question_bank/raw/` | 原始 JSON 题库 |
| `question_bank/cleaned/` | 校验通过的题库和拒绝记录 |
| `question_bank/validation.py` | 清洗、校验和去重 |
| `question_bank/repository.py` | SQLite 结构化存储 |
| `question_bank/import_questions.py` | 题库导入命令 |
| `rag/` | 分块、向量化、Chroma封装与检索服务 |
| `parsers/` | 材料文本提取和结构化解析 |
| `samples/` | 题库、材料、ContextChunk Schema及示例简历/JD |
| `chroma_store/` | 本地Chroma持久化目录，不提交真实数据 |
| `tests/` | 自动测试 |

## 环境

从仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r knowledge\requirements.txt
```

Python建议使用3.11。即使暂时未安装 `chromadb`，SQLite题库、文档解析和本地关键词检索仍然可以运行。

## 1. 导入题库

原始题库必须是JSON数组，字段以 `samples/question.schema.json` 为准。运行：

```powershell
python -m knowledge.question_bank.import_questions knowledge\question_bank\raw\seed_questions.json
```

默认生成：

- `knowledge/question_bank/questions.sqlite3`
- `knowledge/question_bank/cleaned/questions.json`
- `knowledge/question_bank/cleaned/rejected.json`
- `knowledge/chroma_store/` 中的向量数据

导入使用题号进行更新或插入，同一文件可以重复执行。没有安装Chroma时可以明确关闭：

```powershell
python -m knowledge.question_bank.import_questions knowledge\question_bank\raw\seed_questions.json --without-chroma
```

命令返回示例：

```json
{
  "imported": 24,
  "indexed": 24,
  "backend": "sqlite+chroma",
  "accepted": 24,
  "rejected": 0
}
```

## 2. 解析材料

```powershell
python -m knowledge.parsers.parse_file knowledge\samples\resume.txt --type resume --user-id demo
python -m knowledge.parsers.parse_file knowledge\samples\jd.txt --type jd --user-id demo
```

`--type` 支持：

- `resume`
- `jd`
- `project_intro`
- `business_plan`
- `pitch_ppt`（旧名称 `pitch_deck` 仍可输入，但会自动转换）

扫描版PDF没有文本层时会明确报错，需要B在上传流程中先接入OCR服务或要求用户上传可复制文本的文件。

Python调用方式：

```python
from knowledge.parsers import parse_material

material = parse_material(
    "uploads/resume.docx",
    material_type="resume",
    user_id="user-001",
)
payload = material.to_dict()
```

## 3. 检索题目

```powershell
python -m knowledge.rag.query "缓存" --position java_backend --difficulty hard --top-k 5
```

供B和D直接调用的接口：

```python
from knowledge.rag import KnowledgeService

service = KnowledgeService(
    database_path="knowledge/question_bank/questions.sqlite3",
    chroma_directory="knowledge/chroma_store",
)

result = service.search_questions(
    "Redis缓存",
    position="java_backend",
    difficulty="hard",
    question_type="short_answer",
    knowledge_points=["Redis"],
    top_k=5,
)
```

返回结构：

```json
{
  "query": "Redis缓存",
  "questions": [
    {
      "question_id": "java_003",
      "question_type": "short_answer",
      "content": "请说明缓存穿透的含义，并给出两种常见治理方式。",
      "options": [],
      "answer": "参考答案",
      "explanation": "答案解析",
      "knowledge_points": ["Redis", "缓存穿透"]
    }
  ],
  "contexts": [
    {
      "chunk_id": "java_003",
      "source_type": "question_bank",
      "text": "请说明缓存穿透的含义，并给出两种常见治理方式。",
      "metadata": {"score": 0.15, "position": "java_backend", "difficulty": "hard"}
    }
  ],
  "total": 1,
  "backend": "sqlite-keyword",
  "filters": {}
}
```

生成正式试卷时可传 `include_answer=False`，避免把答案返回给前端。

## 4. 索引和检索用户材料（接口模板）

> 本节代码用于说明计划中的调用方式。`search_materials()` 当前仍是接口模板，简历/JD 等材料的正式检索和上下文召回尚未完成，D 暂时应使用模拟材料上下文。

```python
from knowledge.parsers import parse_material
from knowledge.rag import KnowledgeService

service = KnowledgeService(
    database_path="knowledge/question_bank/questions.sqlite3",
    chroma_directory="knowledge/chroma_store",
)

resume = parse_material("uploads/resume.docx", material_type="resume", user_id="u1")
service.index_material(resume)

context = service.search_materials(
    "候选人的Java项目经验",
    user_id="u1",
    material_type="resume",
    top_k=5,
)
```

D的Agent只依赖检索结果JSON，不需要知道SQLite、Chroma或解析器内部实现。

## 5. 自动测试

```powershell
python -m unittest discover -s knowledge\tests -v
```

测试覆盖题库完整性、跨岗位覆盖、重复检测、SQLite导入、筛选检索、简历/JD结构化解析、材料检索和文本分块。

## 与B的集成约定

B在上传接口中：

1. 保存上传文件；
2. 调用 `parse_material()`；
3. 将解析结果保存到自己的材料记录；
4. 调用 `service.index_material()` 建立检索数据；
5. 将 `material_id` 返回给前端。

B在生成笔试接口中调用 `search_questions()`，并设置 `include_answer=False`。

## 与D的集成约定

D可以直接消费：

- `search_questions()` 返回的 `questions`：严格符合 `QuestionBankItem`，用于组卷
- `search_questions()` 返回的 `contexts`：严格符合 `ContextChunk`，用于错题相似题和技术追问
- `search_materials()` 返回的 `contexts`：严格符合 `ContextChunk`，用于简历、JD、项目、商业计划书和PPT上下文

题库检索返回 `query/questions/contexts/total/backend/filters`；材料检索返回 `query/contexts/total/backend/filters`。

## 当前边界

- 种子题用于验证完整流程，不代表正式生产题量；后续应继续扩充并人工审核。
- `search_materials()` 和简历/JD 材料召回当前为接口模板，尚未作为正式能力交付。
- 当前简历/JD结构化采用基础规则提取，不调用大模型，效果仍需完善和验证。
- 扫描PDF暂不内置OCR。
- Chroma是本地持久化方案，Vercel等无持久磁盘环境部署时需要改用外部向量数据库。
