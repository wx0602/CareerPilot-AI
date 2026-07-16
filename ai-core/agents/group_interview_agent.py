from __future__ import annotations

from typing import Any

from agents.llm_client import call_json_model, read_prompt, to_jsonable
from agents.model_imports import REPO_ROOT  # noqa: F401
from models import (
    ReportResponse,
    SimulationFinishRequest,
    SimulationFinishResponse,
    SimulationReportRequest,
    SimulationStartRequest,
    SimulationTurnResponse,
    SimulationUserMessageRequest,
)
from scoring.simulation import validate_evaluation
from skills.definitions import get_skill, skill_to_payload


CANDIDATE_ROLES = {
    "candidate_logic",
    "candidate_collaboration",
    "candidate_challenger",
}

GROUP_STAGE_SEQUENCE = (
    "case_intro",
    "individual_statement",
    "free_discussion",
    "disagreement_resolution",
    "consensus",
    "summary",
    "scoring",
)


class GroupInterviewAgent:
    """Runs structured leaderless group discussions with three AI candidates."""

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        task_type = state["task_type"]
        handlers = {
            "start_session": self.start_session,
            "handle_user_message": self.handle_user_message,
            "finish_session": self.finish_session,
            "generate_report": self.generate_report,
        }
        if task_type not in handlers:
            raise ValueError(f"GroupInterviewAgent 不支持任务：{task_type}")
        return {"response": handlers[task_type](state["request"])}

    def _call(self, action: str, request: Any, response_model: type, temperature: float = 0.4):
        skill = get_skill("group_interview")
        return call_json_model(
            system_prompt=read_prompt(skill.prompt_file),
            user_payload={
                "action": action,
                "request": to_jsonable(request),
                "skill": skill_to_payload(skill),
                "target_schema": response_model.model_json_schema(),
            },
            response_model=response_model,
            temperature=temperature,
        )

    def start_session(self, request: SimulationStartRequest | dict[str, Any]) -> SimulationTurnResponse:
        req = request if isinstance(request, SimulationStartRequest) else SimulationStartRequest.model_validate(request)
        if req.mode != "group_interview":
            raise ValueError("GroupInterviewAgent 仅支持 group_interview")
        response = self._call("start_session", req, SimulationTurnResponse)
        response = response.model_copy(update={"stage": "case_intro", "status": "active"})
        self._validate_response_identity(req.session_id, response)
        return response

    def handle_user_message(
        self, request: SimulationUserMessageRequest | dict[str, Any]
    ) -> SimulationTurnResponse:
        req = (
            request
            if isinstance(request, SimulationUserMessageRequest)
            else SimulationUserMessageRequest.model_validate(request)
        )
        if req.mode != "group_interview":
            raise ValueError("GroupInterviewAgent 仅支持 group_interview")
        last_error: ValueError | None = None
        for _ in range(3):
            response = self._call("handle_user_message", req, SimulationTurnResponse)
            try:
                self._validate_response_identity(req.session_id, response)
                self._validate_candidate_exchange(req, response)
            except ValueError as exc:
                last_error = exc
                continue
            next_stage = self._next_stage(req.stage)
            return response.model_copy(
                update={
                    "stage": next_stage,
                    "status": "completed" if next_stage == "scoring" else "active",
                }
            )
        raise ValueError(f"群体面试连续返回无效候选人互动：{last_error}")

    def finish_session(
        self, request: SimulationFinishRequest | dict[str, Any]
    ) -> SimulationFinishResponse:
        req = request if isinstance(request, SimulationFinishRequest) else SimulationFinishRequest.model_validate(request)
        if req.mode != "group_interview":
            raise ValueError("GroupInterviewAgent 仅支持 group_interview")
        response = self._call("finish_session", req, SimulationFinishResponse, temperature=0.2)
        if response.session_id != req.session_id or response.mode != req.mode:
            raise ValueError("群体面试评分返回了错误的会话或模式")
        validate_evaluation(req.mode, response.evaluation, req.history)
        return response

    def generate_report(self, request: SimulationReportRequest | dict[str, Any]) -> ReportResponse:
        req = request if isinstance(request, SimulationReportRequest) else SimulationReportRequest.model_validate(request)
        if req.mode != "group_interview":
            raise ValueError("GroupInterviewAgent 仅支持 group_interview")
        validate_evaluation(req.mode, req.evaluation, req.history)
        evaluation = req.evaluation
        return ReportResponse(
            session_id=req.session_id,
            mode=req.mode,
            overall_score=evaluation.overall_score,
            dimension_scores=evaluation.dimension_scores,
            strengths=evaluation.strengths,
            weaknesses=evaluation.weaknesses,
            suggestions=evaluation.suggestions,
            charts={
                "radar": evaluation.dimension_scores,
                "evidence": [item.model_dump() for item in evaluation.evidence],
            },
            summary="群体面试报告基于用户在无领导小组讨论中的真实发言生成。",
        )

    @staticmethod
    def _validate_response_identity(session_id: str, response: SimulationTurnResponse) -> None:
        if response.session_id != session_id or response.mode != "group_interview":
            raise ValueError("群体面试返回了错误的会话或模式")

    @staticmethod
    def _next_stage(current_stage: str | None) -> str:
        if current_stage not in GROUP_STAGE_SEQUENCE:
            return "individual_statement"
        index = GROUP_STAGE_SEQUENCE.index(current_stage)
        return GROUP_STAGE_SEQUENCE[min(index + 1, len(GROUP_STAGE_SEQUENCE) - 1)]

    @staticmethod
    def _validate_candidate_exchange(
        request: SimulationUserMessageRequest,
        response: SimulationTurnResponse,
    ) -> None:
        candidate_messages = [item for item in response.messages if item.speaker in CANDIDATE_ROLES]
        present_roles = {item.speaker for item in candidate_messages}
        if present_roles != CANDIDATE_ROLES:
            raise ValueError("群体讨论每轮必须包含三种 AI 候选人的发言")
        candidate_ids = {
            item.message_id
            for item in [*request.history, *response.messages]
            if item.speaker in CANDIDATE_ROLES
        }
        if not any(
            item.reply_to in candidate_ids and item.reply_to != item.message_id
            for item in candidate_messages
        ):
            raise ValueError("AI 候选人必须通过 reply_to 相互回应")
