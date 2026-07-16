from __future__ import annotations

from typing import Any
from uuid import uuid4

from agents.llm_client import call_json_model, read_prompt, to_jsonable
from agents.model_imports import REPO_ROOT  # noqa: F401
from models import (
    ReportResponse,
    SimulationFinishRequest,
    SimulationFinishResponse,
    SimulationMessage,
    SimulationReportRequest,
    SimulationStartRequest,
    SimulationTurnResponse,
    SimulationUserMessageRequest,
)
from scoring.simulation import (
    detect_stress_control,
    lower_stress_level,
    validate_evaluation,
    validate_safe_pressure,
)
from skills.definitions import get_skill, skill_to_payload


class StressInterviewAgent:
    """Runs adaptive but non-abusive pressure interviews."""

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        task_type = state["task_type"]
        handlers = {
            "start_session": self.start_session,
            "handle_user_message": self.handle_user_message,
            "finish_session": self.finish_session,
            "generate_report": self.generate_report,
        }
        if task_type not in handlers:
            raise ValueError(f"StressInterviewAgent 不支持任务：{task_type}")
        return {"response": handlers[task_type](state["request"])}

    def _call(self, action: str, request: Any, response_model: type, temperature: float = 0.3):
        skill = get_skill("stress_interview")
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
        if req.mode != "stress_interview":
            raise ValueError("StressInterviewAgent 仅支持 stress_interview")
        response = self._call("start_session", req, SimulationTurnResponse)
        if response.stress_level is None:
            response = response.model_copy(update={"stress_level": req.stress_level or "medium"})
        self._validate_response(req.session_id, response)
        return response

    def handle_user_message(
        self, request: SimulationUserMessageRequest | dict[str, Any]
    ) -> SimulationTurnResponse:
        req = (
            request
            if isinstance(request, SimulationUserMessageRequest)
            else SimulationUserMessageRequest.model_validate(request)
        )
        if req.mode != "stress_interview":
            raise ValueError("StressInterviewAgent 仅支持 stress_interview")
        control = detect_stress_control(req.user_message)
        if control:
            return self._control_response(req, control)
        response = self._call("handle_user_message", req, SimulationTurnResponse)
        self._validate_response(req.session_id, response)
        return response

    def finish_session(
        self, request: SimulationFinishRequest | dict[str, Any]
    ) -> SimulationFinishResponse:
        req = request if isinstance(request, SimulationFinishRequest) else SimulationFinishRequest.model_validate(request)
        if req.mode != "stress_interview":
            raise ValueError("StressInterviewAgent 仅支持 stress_interview")
        response = self._call("finish_session", req, SimulationFinishResponse, temperature=0.2)
        if response.session_id != req.session_id or response.mode != req.mode:
            raise ValueError("压力面试评分返回了错误的会话或模式")
        validate_evaluation(req.mode, response.evaluation, req.history)
        return response

    def generate_report(self, request: SimulationReportRequest | dict[str, Any]) -> ReportResponse:
        req = request if isinstance(request, SimulationReportRequest) else SimulationReportRequest.model_validate(request)
        if req.mode != "stress_interview":
            raise ValueError("StressInterviewAgent 仅支持 stress_interview")
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
            summary="压力面试报告基于用户在连续追问中的真实发言生成。",
        )

    @staticmethod
    def _validate_response(session_id: str, response: SimulationTurnResponse) -> None:
        if response.session_id != session_id or response.mode != "stress_interview":
            raise ValueError("压力面试返回了错误的会话或模式")
        validate_safe_pressure(response.messages)

    @staticmethod
    def _control_response(
        request: SimulationUserMessageRequest,
        control: str,
    ) -> SimulationTurnResponse:
        level = request.stress_level or "medium"
        if control == "stop":
            status = "completed"
            stage = "closing"
            content = "已立即停止压力追问。你可以结束会话并生成本次训练报告。"
        elif control == "pause":
            status = "paused"
            stage = "paused"
            content = "已暂停压力面试。准备好后发送新的回答即可继续。"
        else:
            status = "active"
            stage = request.stage if request.stage not in (None, "paused") else "probing"
            level = lower_stress_level(level)
            content = f"已将压力等级调整为 {level}，后续只进行更温和的事实澄清。"
        return SimulationTurnResponse(
            session_id=request.session_id,
            mode=request.mode,
            stage=stage,
            status=status,
            stress_level=level,
            control_acknowledged=True,
            messages=[
                SimulationMessage(
                    message_id=f"control_{uuid4().hex[:12]}",
                    speaker="interviewer",
                    display_name="压力面试官",
                    content=content,
                )
            ],
        )
