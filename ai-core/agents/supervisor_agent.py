from __future__ import annotations

from typing import Any


class SupervisorAgent:
    """识别任务类型，并把 LangGraph State 路由到对应 Agent。"""

    ROUTES = {
        "generate_exam": "exam_agent",
        "grade_exam": "exam_agent",
        "generate_question": "interview_agent",
        "evaluate_answer": "evaluation_agent",
        "generate_report": "report_agent",
    }

    SIMULATION_ROUTES = {
        "group_interview": "group_interview_agent",
        "stress_interview": "stress_interview_agent",
    }

    SIMULATION_TASKS = {
        "start_session",
        "handle_user_message",
        "finish_session",
        "generate_report",
    }

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        task_type = state.get("task_type")
        request = state.get("request")
        mode = request.get("mode") if isinstance(request, dict) else getattr(request, "mode", None)
        if task_type in self.SIMULATION_TASKS and mode in self.SIMULATION_ROUTES:
            return {"next_agent": self.SIMULATION_ROUTES[mode]}
        if task_type not in self.ROUTES:
            raise ValueError(f"SupervisorAgent 无法识别任务：{task_type}")
        return {"next_agent": self.ROUTES[task_type]}


def route_next_agent(state: dict[str, Any]) -> str:
    return state["next_agent"]
