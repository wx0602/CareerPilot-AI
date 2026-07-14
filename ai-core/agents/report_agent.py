from __future__ import annotations

from typing import Any

from agents.llm_client import call_json_model, read_prompt, to_jsonable
from agents.model_imports import REPO_ROOT  # noqa: F401
from models import ReportRequest, ReportResponse
from skills.definitions import get_skill, skill_to_payload


class ReportAgent:
    """负责生成综合报告、改进建议和图表 JSON 数据。"""

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        if state["task_type"] != "generate_report":
            raise ValueError(f"ReportAgent 不支持任务：{state['task_type']}")
        return {"response": self.generate_report(state["request"])}

    def generate_report(self, request: ReportRequest | dict[str, Any]) -> ReportResponse:
        req = request if isinstance(request, ReportRequest) else ReportRequest.model_validate(request)
        skill = get_skill("report_generation")
        # 这里只产出图表数据，具体渲染方式交给前端决定。
        return call_json_model(
            system_prompt=read_prompt(skill.prompt_file),
            user_payload={
                "request": to_jsonable(req),
                "skill": skill_to_payload(skill),
                "target_schema": ReportResponse.model_json_schema(),
                "chart_requirements": {
                    "radar": "各评分维度 0-100 分，用于雷达图。",
                    "score_trend": "如有多轮面试，按轮次输出分数变化。",
                    "knowledge_scores": "如有笔试结果，按知识点汇总表现。",
                },
            },
            response_model=ReportResponse,
            temperature=0.2,
        )


def generate_report(request: ReportRequest | dict[str, Any]) -> ReportResponse:
    from agents.workflow import run_workflow

    return run_workflow({"task_type": "generate_report", "request": request})
