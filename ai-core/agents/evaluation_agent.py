from __future__ import annotations

from typing import Any

from agents.llm_client import call_json_model, read_prompt, to_jsonable
from agents.model_imports import REPO_ROOT  # noqa: F401
from models import EvaluateAnswerRequest, EvaluationResponse
from skills.definitions import get_interview_skill, skill_to_payload


class EvaluationAgent:
    """负责对面试回答进行多维度评分，并按需生成追问。"""

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        if state["task_type"] != "evaluate_answer":
            raise ValueError(f"EvaluationAgent 不支持任务：{state['task_type']}")
        return {"response": self.evaluate_answer(state["request"])}

    def evaluate_answer(self, request: EvaluateAnswerRequest | dict[str, Any]) -> EvaluationResponse:
        req = (
            request
            if isinstance(request, EvaluateAnswerRequest)
            else EvaluateAnswerRequest.model_validate(request)
        )
        skill = get_interview_skill(req.mode)
        # 评分维度来自当前面试 Skill，输出仍严格校验为 EvaluationResponse。
        return call_json_model(
            system_prompt=read_prompt("answer_evaluation.md"),
            user_payload={
                "request": to_jsonable(req),
                "skill": skill_to_payload(skill),
                "target_schema": EvaluationResponse.model_json_schema(),
            },
            response_model=EvaluationResponse,
            temperature=0.2,
        )


def evaluate_answer(request: EvaluateAnswerRequest | dict[str, Any]) -> EvaluationResponse:
    from agents.workflow import run_workflow

    return run_workflow({"task_type": "evaluate_answer", "request": request})
