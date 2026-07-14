"""
shared/models.py

项目第一阶段的公共数据模型。

主要作用：
1. C 模块按照这些格式提供题库和 RAG 检索结果。
2. D 模块按照这些格式接收数据，并返回试卷、评分和报告。
3. B 模块可以直接将这些模型用于 FastAPI 请求和响应。
4. A 模块不需要导入本文件，只需要按照后端返回的 JSON 展示页面。

环境：
- Python 3.11+
- Pydantic 2.x
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


# ============================================================
# 1. 通用类型
# ============================================================

# 系统支持的三种训练模式。
# job：
# 普通求职面试，主要根据简历和岗位 JD 提问。
# technical：
# 技术面试，可以根据简历、JD 和笔试错题提问。
# pitch：
# 创业路演答辩，根据商业计划书和路演 PPT 提问。
InterviewMode = Literal[
    "job",
    "technical",
    "pitch",
]


# 题目或面试问题的难度。
Difficulty = Literal[
    "easy",
    "medium",
    "hard",
]


# 当前系统支持的笔试题型。
QuestionType = Literal[
    "single_choice",    # 单选题
    "multiple_choice",  # 多选题
    "true_false",       # 判断题
    "short_answer",     # 简答题
]


# 所有百分制评分统一使用 0～100 的整数。
Score = Annotated[
    int,
    Field(ge=0, le=100),
]


# ============================================================
# 2. C 提供给 D 的公共上下文
# ============================================================

class ContextChunk(BaseModel):
    """
    C 的 RAG 模块返回的一段检索内容。

    一份简历、JD、商业计划书或题库文档可能会被分成多个文本片段。
    C 检索出相关片段后，按照这个格式交给 D。

    示例：
    {
        "chunk_id": "resume_001",
        "source_type": "resume",
        "text": "参与商城系统开发，负责 Redis 缓存模块。",
        "metadata": {
            "filename": "resume.pdf",
            "page": 1
        }
    }
    """

    # 当前文本片段的唯一编号。
    chunk_id: str

    # 文本来源。
    #
    # 建议使用：
    # resume          简历
    # jd              岗位描述
    # wrong_question  笔试错题
    # question_bank   题库
    # business_plan   商业计划书
    # pitch_ppt       路演 PPT
    source_type: str

    # 实际检索到的文本内容。
    text: str

    # 其他附加信息，例如文件名、页码、相似度等。
    # 由于不同来源的附加信息可能不同，
    # 第一阶段使用通用字典保存。
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class CandidateProfile(BaseModel):
    """
    候选人的基础信息。

    这些信息可以由用户填写，
    也可以由 C 从简历和 JD 中解析得到。
    """

    # 候选人姓名，可以为空。
    name: str | None = None

    # 目标岗位，例如“Java 后端工程师”。
    target_position: str | None = None

    # 目标企业，可以为空。
    target_company: str | None = None


class HistoryItem(BaseModel):
    """
    一轮历史问答。

    D 在生成新问题时，可以读取历史问答，
    避免重复提问，并根据用户之前的回答继续追问。
    """

    # 当前问题的唯一编号。
    question_id: str

    # 面试官提出的问题。
    question: str

    # 用户的回答。
    #
    # 在问题刚生成、用户还没有回答时，可以为空。
    answer: str | None = None


# ============================================================
# 3. 笔试题库
# ============================================================

class QuestionOption(BaseModel):
    """
    选择题的一个选项。

    示例：
    {
        "key": "A",
        "text": "ArrayList"
    }
    """

    # 选项编号，例如 A、B、C、D。
    key: str

    # 选项正文。
    text: str


class QuestionBankItem(BaseModel):
    """
    C 提供的完整题库题目。

    这个模型包含正确答案，因此只能在后端内部使用，
    不能直接返回给前端。

    单选题示例：
    {
        "question_id": "java_001",
        "question_type": "single_choice",
        "content": "下面哪个集合是线程安全的？",
        "options": [
            {"key": "A", "text": "ArrayList"},
            {"key": "B", "text": "CopyOnWriteArrayList"}
        ],
        "answer": "B",
        "explanation": "CopyOnWriteArrayList 是线程安全集合。",
        "knowledge_points": ["Java 集合", "并发编程"]
    }
    """

    # 题目的唯一编号。
    question_id: str

    # 题型。
    question_type: QuestionType

    # 题目正文。
    content: str

    # 选择题选项。
    #
    # 判断题和简答题可以使用空列表。
    options: list[QuestionOption] = Field(
        default_factory=list
    )

    # 正确答案或参考答案。
    # 单选题：
    # "B"
    # 多选题：
    # ["A", "C"]
    # 判断题：
    # "true" 或 "false"
    # 简答题：
    # 可以保存参考答案文本。
    answer: str | list[str] | None = None

    # 题目解析。
    explanation: str | None = None

    # 该题涉及的知识点。
    knowledge_points: list[str] = Field(
        default_factory=list
    )


# ============================================================
# 4. 生成试卷
# ============================================================

class GenerateExamRequest(BaseModel):
    """
    B 请求 D 生成一套试卷时传入的数据。

    第一阶段只保留最基础的条件，
    不规定必须有多少道单选题、判断题和简答题。
    具体题型组合由 D 的组卷逻辑决定。
    """

    # 当前训练会话编号。
    session_id: str

    # 目标岗位，例如“Java 后端工程师”。
    position: str

    # 目标企业，可以为空。
    company: str | None = None

    # 试卷整体难度。
    difficulty: Difficulty = "medium"

    # 希望生成的题目总数。
    question_count: int = Field(
        default=10,
        gt=0,
    )


class ExamQuestion(BaseModel):
    """
    返回给前端的一道笔试题。

    与 QuestionBankItem 的区别：

    QuestionBankItem：
    后端内部使用，包含正确答案和解析。

    ExamQuestion：
    返回给前端，不包含正确答案和解析。
    """

    # 题目编号。
    question_id: str

    # 题型。
    question_type: QuestionType

    # 题目正文。
    content: str

    # 选择题选项。
    options: list[QuestionOption] = Field(
        default_factory=list
    )


class ExamPaperResponse(BaseModel):
    """
    D 生成的一套笔试试卷。

    B 可以将该对象直接返回给 A。
    """

    # 试卷唯一编号。
    exam_id: str

    # 当前训练会话编号。
    session_id: str

    # 试卷标题。
    title: str

    # 试卷中的全部题目。
    questions: list[ExamQuestion] = Field(
        default_factory=list
    )


# ============================================================
# 5. 用户提交笔试答案
# ============================================================

class SubmittedAnswer(BaseModel):
    """
    用户对一道题的回答。

    单选题：
    {
        "question_id": "q001",
        "answer": "B"
    }

    多选题：
    {
        "question_id": "q002",
        "answer": ["A", "C"]
    }

    简答题：
    {
        "question_id": "q003",
        "answer": "缓存穿透是指查询不存在的数据……"
    }
    """

    # 题目编号。
    question_id: str

    # 用户答案。
    answer: str | list[str]


class ExamSubmission(BaseModel):
    """
    用户提交的整套笔试答案。
    """

    # 当前训练会话编号。
    session_id: str

    # 对应试卷编号。
    exam_id: str

    # 用户对所有题目的回答。
    answers: list[SubmittedAnswer] = Field(
        default_factory=list
    )


# ============================================================
# 6. 笔试批改结果
# ============================================================

class ExamResultResponse(BaseModel):
    """
    D 返回的整套笔试结果。

    第一阶段不再为每种批改结果建立独立模型，
    单题结果暂时使用字典表示。
    """

    # 对应试卷编号。
    exam_id: str

    # 笔试总评分，范围为 0～100。
    score: Score

    # 每道题的批改结果。
    #
    # 示例：
    # [
    #     {
    #         "question_id": "q001",
    #         "correct": false,
    #         "user_answer": "A",
    #         "correct_answer": "B",
    #         "feedback": "CopyOnWriteArrayList 是线程安全集合。"
    #     }
    # ]
    question_results: list[dict[str, Any]] = Field(
        default_factory=list
    )

    # 根据错题分析出的薄弱点。
    weaknesses: list[str] = Field(
        default_factory=list
    )

    # 针对薄弱点给出的改进建议。
    suggestions: list[str] = Field(
        default_factory=list
    )


# ============================================================
# 7. 生成面试问题
# ============================================================

class GenerateQuestionRequest(BaseModel):
    """
    B 请求 D 生成一个面试问题时传入的数据。

    D 可以根据：
    - 面试模式
    - 候选人信息
    - RAG 检索结果
    - 历史问答

    生成新的面试问题。
    """

    # 当前训练会话编号。
    session_id: str

    # 求职、技术或路演模式。
    mode: InterviewMode

    # 候选人的基础信息。
    candidate_profile: CandidateProfile = Field(
        default_factory=CandidateProfile
    )

    # C 检索出的简历、JD、错题或路演材料。
    contexts: list[ContextChunk] = Field(
        default_factory=list
    )

    # 之前已经进行的问答。
    history: list[HistoryItem] = Field(
        default_factory=list
    )


class QuestionResponse(BaseModel):
    """
    D 返回的一道面试问题。
    """

    # 问题唯一编号。
    question_id: str

    # 问题正文。
    question: str


# ============================================================
# 8. 面试回答评分与追问
# ============================================================

class EvaluateAnswerRequest(BaseModel):
    """
    B 请求 D 对用户的一次面试回答进行评分。
    """

    # 当前训练会话编号。
    session_id: str

    # 当前面试模式。
    mode: InterviewMode

    # 当前问题编号。
    question_id: str

    # 当前问题正文。
    question: str

    # 用户回答。
    answer: str


class EvaluationResponse(BaseModel):
    """
    D 对一次面试回答的评价结果。
    """

    # 当前问题编号。
    question_id: str

    # 本次回答总分，范围为 0～100。
    score: Score

    # 各维度得分。
    #
    # 技术面试示例：
    # {
    #     "专业知识": 80,
    #     "逻辑表达": 75,
    #     "项目深度": 70
    # }
    #
    # 路演示例：
    # {
    #     "商业逻辑": 85,
    #     "市场价值": 80,
    #     "表达能力": 78
    # }
    dimension_scores: dict[str, Score] = Field(
        default_factory=dict
    )

    # 回答中的优点。
    strengths: list[str] = Field(
        default_factory=list
    )

    # 回答中的不足。
    weaknesses: list[str] = Field(
        default_factory=list
    )

    # 是否需要继续追问。
    need_followup: bool = False

    # 需要追问时，由 D 直接生成下一道追问。
    #
    # need_followup=False 时，该字段可以为空。
    followup_question: str | None = None


# ============================================================
# 9. 综合报告
# ============================================================

class ReportRequest(BaseModel):
    """
    B 请求 D 生成最终报告时传入的数据。

    可以只包含笔试结果，
    也可以只包含面试评价，
    还可以同时包含两者。
    """

    # 当前训练会话编号。
    session_id: str

    # 当前训练模式。
    mode: InterviewMode

    # 笔试结果。
    #
    # 求职面试或路演模式可能没有笔试，因此允许为空。
    exam_result: ExamResultResponse | None = None

    # 每一轮面试回答的评价结果。
    interview_evaluations: list[EvaluationResponse] = Field(
        default_factory=list
    )


class ReportResponse(BaseModel):
    """
    D 返回的最终综合报告。

    A 可以根据该 JSON 展示：
    - 总分
    - 分项得分
    - 优点
    - 薄弱点
    - 改进建议
    - 雷达图
    - 知识点柱状图
    """

    # 当前训练会话编号。
    session_id: str

    # 当前训练模式。
    mode: InterviewMode

    # 综合总分，范围为 0～100。
    overall_score: Score

    # 各维度得分。
    dimension_scores: dict[str, Score] = Field(
        default_factory=dict
    )

    # 综合表现中的优点。
    strengths: list[str] = Field(
        default_factory=list
    )

    # 综合表现中的不足。
    weaknesses: list[str] = Field(
        default_factory=list
    )

    # 改进建议。
    suggestions: list[str] = Field(
        default_factory=list
    )

    # 图表需要的数据。
    #
    # D 只负责输出数据，
    # A 使用 Vue 和 ECharts 绘制实际图表。
    #
    # 示例：
    # {
    #     "radar": {
    #         "专业知识": 80,
    #         "逻辑表达": 85,
    #         "岗位匹配": 78
    #     },
    #     "knowledge_scores": {
    #         "Java": 85,
    #         "Redis": 45,
    #         "MySQL": 60
    #     }
    # }
    charts: dict[str, Any] = Field(
        default_factory=dict
    )

    # 对本次训练结果的整体总结。
    summary: str