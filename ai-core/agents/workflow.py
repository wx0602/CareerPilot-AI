from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal, TypedDict

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - 依赖缺失时给出明确错误
    END = None
    StateGraph = None

from agents.evaluation_agent import EvaluationAgent
from agents.exam_agent import ExamAgent
from agents.interview_agent import InterviewAgent
from agents.report_agent import ReportAgent
from agents.supervisor_agent import SupervisorAgent, route_next_agent


TaskType = Literal[
    "generate_exam",
    "grade_exam",
    "generate_question",
    "evaluate_answer",
    "generate_report",
]


class AgentState(TypedDict, total=False):
    # LangGraph 共享 State：Supervisor 写入 next_agent，各业务 Agent 写入 response。
    task_type: TaskType
    request: Any
    question_bank: Any
    expected_question_ids: Any
    next_agent: str
    response: Any


def _require_langgraph() -> None:
    if StateGraph is None or END is None:
        raise RuntimeError("缺少 LangGraph 依赖，请先安装 ai-core/requirements.txt。")


@lru_cache(maxsize=1)
def build_workflow() -> Any:
    _require_langgraph()
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", SupervisorAgent())
    graph.add_node("exam_agent", ExamAgent())
    graph.add_node("interview_agent", InterviewAgent())
    graph.add_node("evaluation_agent", EvaluationAgent())
    graph.add_node("report_agent", ReportAgent())

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_next_agent,
        {
            "exam_agent": "exam_agent",
            "interview_agent": "interview_agent",
            "evaluation_agent": "evaluation_agent",
            "report_agent": "report_agent",
        },
    )
    graph.add_edge("exam_agent", END)
    graph.add_edge("interview_agent", END)
    graph.add_edge("evaluation_agent", END)
    graph.add_edge("report_agent", END)
    return graph.compile()


def run_workflow(state: AgentState) -> Any:
    # 公共函数兼容入口：统一进入 Supervisor，再由条件边路由到具体 Agent。
    result = build_workflow().invoke(state)
    return result["response"]
