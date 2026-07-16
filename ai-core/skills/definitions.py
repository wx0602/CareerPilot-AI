from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    agent: str
    prompt_file: str
    description: str
    inputs: list[str]
    outputs: list[str]
    dimensions: dict[str, str]


SKILLS: dict[str, SkillDefinition] = {
    "written_exam": SkillDefinition(
        name="written_exam",
        agent="ExamAgent",
        prompt_file="written_exam.md",
        description="用于笔试组卷、错题分析和薄弱点总结。",
        inputs=["岗位", "企业", "难度", "题库内容", "用户提交答案"],
        outputs=["不含答案的试卷", "客观题批改结果", "错题分析", "薄弱点总结"],
        dimensions={
            "题目覆盖": "题目是否覆盖岗位需要的关键知识点。",
            "难度匹配": "题目难度是否符合请求难度。",
            "错题分析": "能否从错误题目提炼薄弱知识点。",
        },
    ),
    "short_answer_grading": SkillDefinition(
        name="short_answer_grading",
        agent="ExamAgent",
        prompt_file="short_answer_grading.md",
        description="用于简答题的大模型评分。",
        inputs=["题目", "用户回答", "参考答案", "解析", "知识点"],
        outputs=["0-100 分", "回答优点", "遗漏内容", "具体反馈"],
        dimensions={
            "语义正确": "是否覆盖参考答案的关键语义。",
            "概念完整": "是否说明关键概念、条件和边界。",
            "表达清晰": "是否结构清楚、表述准确。",
        },
    ),
    "job_interview": SkillDefinition(
        name="job_interview",
        agent="InterviewAgent",
        prompt_file="job_interview.md",
        description="专业 HR 面试官，主要使用简历和岗位 JD。",
        inputs=["候选人资料", "简历片段", "岗位 JD", "历史问答"],
        outputs=["求职面试问题", "追问方向"],
        dimensions={
            "岗位匹配": "经历、能力与目标岗位要求的贴合程度。",
            "经历相关性": "过往经历是否能支撑岗位要求。",
            "逻辑表达": "回答是否有结构和重点。",
            "沟通能力": "表达是否自然、清晰、有互动意识。",
            "应变能力": "能否回应压力问题和边界场景。",
        },
    ),
    "technical_interview": SkillDefinition(
        name="technical_interview",
        agent="InterviewAgent",
        prompt_file="technical_interview.md",
        description="技术面试官，主要使用简历、JD、笔试错题和题库内容。",
        inputs=["候选人资料", "简历片段", "JD", "笔试错题", "题库内容", "历史问答"],
        outputs=["技术面试问题", "技术追问"],
        dimensions={
            "专业知识": "基础概念、关键原理和边界条件的掌握程度。",
            "回答正确性": "回答是否准确，是否存在明显技术错误。",
            "项目深度": "能否结合真实项目说明设计、取舍和结果。",
            "逻辑表达": "技术回答是否有层次和因果关系。",
            "问题分析": "能否定位问题、拆解原因并提出方案。",
        },
    ),
    "pitch_interview": SkillDefinition(
        name="pitch_interview",
        agent="InterviewAgent",
        prompt_file="pitch_interview.md",
        description="投资人或路演评委，主要使用商业计划书和路演 PPT。",
        inputs=["商业计划书", "路演 PPT", "项目材料", "历史问答"],
        outputs=["路演答辩问题", "投资人追问"],
        dimensions={
            "商业逻辑": "商业模式、收入来源和关键假设是否成立。",
            "市场价值": "目标用户、痛点和市场空间是否清楚。",
            "可行性": "资源、路径、风险和里程碑是否可信。",
            "创新性": "方案是否有差异化和竞争壁垒。",
            "表达能力": "答辩是否直接、有说服力并能处理质疑。",
        },
    ),
    "group_interview": SkillDefinition(
        name="group_interview",
        agent="GroupInterviewAgent",
        prompt_file="group_interview.md",
        description="模拟一名用户、三名不同风格 AI 候选人与一名 AI 面试官的无领导小组讨论。",
        inputs=["案例", "用户发言", "所有参与者历史发言", "当前讨论阶段"],
        outputs=["多角色结构化发言", "阶段推进", "引用用户原话的八维评分"],
        dimensions={
            "逻辑": "观点、论据与结论是否连贯。",
            "表达": "发言是否清晰、简洁、有结构。",
            "参与度": "是否持续贡献有效信息并推动讨论。",
            "协作": "是否吸收并发展其他成员的观点。",
            "倾听": "是否准确回应其他参与者的具体发言。",
            "领导力": "是否明确目标、组织流程并推动决策。",
            "冲突处理": "是否处理分歧而非回避或压制。",
            "总结能力": "是否提炼共识、分歧与行动结论。",
        },
    ),
    "stress_interview": SkillDefinition(
        name="stress_interview",
        agent="StressInterviewAgent",
        prompt_file="stress_interview.md",
        description="通过连续追问与证据质疑训练候选人在压力下的回答质量。",
        inputs=["用户回答", "历史问答", "压力等级", "识别出的回答缺口"],
        outputs=["安全的结构化追问", "动态压力等级", "引用用户原话的八维评分"],
        dimensions={
            "稳定性": "面对追问时能否保持稳定和专注。",
            "逻辑一致性": "多轮回答是否前后一致。",
            "证据质量": "是否提供数据、事实和可核验细节。",
            "应变能力": "能否快速识别问题并调整回答。",
            "直接性": "是否直接回答问题而非回避。",
            "可信度": "个人贡献、事实与结论是否可信。",
            "表达": "压力下表达是否清晰有序。",
            "反思能力": "能否承认不足并提出改进。",
        },
    ),
    "report_generation": SkillDefinition(
        name="report_generation",
        agent="ReportAgent",
        prompt_file="report_generation.md",
        description="用于综合笔试结果和多轮面试评分。",
        inputs=["笔试结果", "多轮面试评分", "训练模式"],
        outputs=["总分", "分项得分", "优点", "不足", "改进建议", "总结", "图表数据"],
        dimensions={
            "一致性": "报告内容必须与实际评分结果一致。",
            "具体性": "建议必须具体、可执行。",
            "可视化": "只输出 radar、knowledge_scores 等 JSON 图表数据。",
        },
    ),
}


MODE_TO_INTERVIEW_SKILL = {
    "job": "job_interview",
    "technical": "technical_interview",
    "pitch": "pitch_interview",
    "group_interview": "group_interview",
    "stress_interview": "stress_interview",
}


def get_skill(name: str) -> SkillDefinition:
    if name not in SKILLS:
        raise ValueError(f"不支持的 Skill：{name}")
    return SKILLS[name]


def get_interview_skill(mode: str) -> SkillDefinition:
    return get_skill(MODE_TO_INTERVIEW_SKILL[mode])


def skill_to_payload(skill: SkillDefinition) -> dict[str, Any]:
    return {
        "name": skill.name,
        "agent": skill.agent,
        "description": skill.description,
        "inputs": skill.inputs,
        "outputs": skill.outputs,
        "dimensions": skill.dimensions,
    }
