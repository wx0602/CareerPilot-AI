from __future__ import annotations

from typing import Any

from models import (
    ReportResponse,
    SimulationFinishRequest,
    SimulationFinishResponse,
    SimulationReportRequest,
    SimulationStartRequest,
    SimulationTurnResponse,
    SimulationUserMessageRequest,
)


def start_session(request: SimulationStartRequest | dict[str, Any]) -> SimulationTurnResponse:
    from agents.workflow import run_workflow

    return run_workflow({"task_type": "start_session", "request": request})


def handle_user_message(
    request: SimulationUserMessageRequest | dict[str, Any]
) -> SimulationTurnResponse:
    from agents.workflow import run_workflow

    return run_workflow({"task_type": "handle_user_message", "request": request})


def finish_session(request: SimulationFinishRequest | dict[str, Any]) -> SimulationFinishResponse:
    from agents.workflow import run_workflow

    return run_workflow({"task_type": "finish_session", "request": request})


def generate_simulation_report(
    request: SimulationReportRequest | dict[str, Any]
) -> ReportResponse:
    from agents.workflow import run_workflow

    return run_workflow({"task_type": "generate_report", "request": request})
