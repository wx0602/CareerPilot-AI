from __future__ import annotations

from typing import Any
from uuid import uuid4

from agents.llm_client import call_json_model, read_prompt, to_jsonable
from agents.model_imports import REPO_ROOT  # noqa: F401
from models import GenerateQuestionRequest, QuestionResponse
from skills.definitions import get_interview_skill, skill_to_payload


class InterviewAgent:
    """负责生成求职、技术和路演问题。"""

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        if state["task_type"] != "generate_question":
            raise ValueError(f"InterviewAgent 不支持任务：{state['task_type']}")
        return {"response": self.generate_question(state["request"])}

    def generate_question(self, request: GenerateQuestionRequest | dict[str, Any]) -> QuestionResponse:
        req = (
            request
            if isinstance(request, GenerateQuestionRequest)
            else GenerateQuestionRequest.model_validate(request)
        )
        skill = get_interview_skill(req.mode)
        # 将对应面试 Skill 放入 prompt payload，避免不同模式的问题混用。
        payload = {
            "session_id": req.session_id,
            "mode": req.mode,
            "skill": skill_to_payload(skill),
            "candidate_profile": to_jsonable(req.candidate_profile),
            "contexts": to_jsonable(req.contexts),
            "history": to_jsonable(req.history),
            "target_schema": QuestionResponse.model_json_schema(),
            "question_id_rule": "如果无法确定编号，请使用传入的 suggested_question_id。",
            "suggested_question_id": f"q_{uuid4().hex[:12]}",
        }
        return call_json_model(
            system_prompt=read_prompt(skill.prompt_file),
            user_payload=payload,
            response_model=QuestionResponse,
            temperature=0.4,
        )


def generate_question(request: GenerateQuestionRequest | dict[str, Any]) -> QuestionResponse:
    from agents.workflow import run_workflow

    return run_workflow({"task_type": "generate_question", "request": request})
