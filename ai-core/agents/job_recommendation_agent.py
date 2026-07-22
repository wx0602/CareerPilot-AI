from __future__ import annotations

from typing import Any

from agents.llm_client import call_json_model, read_prompt, to_jsonable
from agents.model_imports import REPO_ROOT  # noqa: F401
from models import (
    CandidateProfileBuildInput,
    JobCandidateProfile,
    RecommendationExplanationRequest,
    RecommendationExplanationResponse,
)


class JobRecommendationAgent:
    """只生成画像与解释，不生成或改写任何岗位事实字段。"""

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        task_type = state["task_type"]
        if task_type == "build_candidate_profile":
            response = self.build_candidate_profile(state["request"])
        elif task_type == "explain_job_recommendations":
            response = self.explain_recommendations(state["request"])
        else:
            raise ValueError(f"JobRecommendationAgent 不支持任务：{task_type}")
        return {"response": response}

    def build_candidate_profile(
        self, request: CandidateProfileBuildInput | dict[str, Any]
    ) -> JobCandidateProfile:
        req = (
            request
            if isinstance(request, CandidateProfileBuildInput)
            else CandidateProfileBuildInput.model_validate(request)
        )
        return call_json_model(
            system_prompt=read_prompt("job_recommendation.md"),
            user_payload={
                "task": "build_candidate_profile",
                "input": to_jsonable(req),
                "target_schema": JobCandidateProfile.model_json_schema(),
            },
            response_model=JobCandidateProfile,
            temperature=0.1,
        )

    def explain_recommendations(
        self, request: RecommendationExplanationRequest | dict[str, Any]
    ) -> RecommendationExplanationResponse:
        req = (
            request
            if isinstance(request, RecommendationExplanationRequest)
            else RecommendationExplanationRequest.model_validate(request)
        )
        return call_json_model(
            system_prompt=read_prompt("job_recommendation.md"),
            user_payload={
                "task": "explain_recommendations",
                "input": to_jsonable(req),
                "target_schema": RecommendationExplanationResponse.model_json_schema(),
                "fact_boundary": "只输出 job_id、推荐理由和改进建议，不得补充或修改岗位、公司、薪资、城市、链接。",
            },
            response_model=RecommendationExplanationResponse,
            temperature=0.2,
        )


def build_candidate_profile(request: CandidateProfileBuildInput | dict[str, Any]) -> JobCandidateProfile:
    from agents.workflow import run_workflow

    return run_workflow({"task_type": "build_candidate_profile", "request": request})


def explain_job_recommendations(
    request: RecommendationExplanationRequest | dict[str, Any]
) -> RecommendationExplanationResponse:
    from agents.workflow import run_workflow

    return run_workflow({"task_type": "explain_job_recommendations", "request": request})
