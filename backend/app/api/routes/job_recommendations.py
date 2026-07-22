from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import JobCandidateProfile

from ..deps import get_current_token, get_db, owned_training_session
from ...core.errors import api_error
from ...dbmodels import AuthToken, Material, Report, TrainingSession
from ...schemas.api import (
    JobInterviewStartRequest,
    JobProfileBuildRequest,
    JobRecommendationItem,
    JobRecommendationSearchRequest,
    JobRecommendationSearchResponse,
    TrainingSessionResponse,
)
from ...services.job_recommendations import (
    CandidateProfileBuilder,
    JSearchAPIError,
    JSearchConfigurationError,
    JSearchTimeoutError,
    JobRecommendationService,
    SeedDataError,
)


router = APIRouter(prefix="/job-recommendations", tags=["岗位推荐"])


def _owner_condition(token: AuthToken):
    if token.is_guest:
        return TrainingSession.created_by_token_id == token.id
    return TrainingSession.owner_user_id == token.user_id


def _recent_report(db: Session, token: AuthToken) -> dict | None:
    row = db.scalar(
        select(Report)
        .join(TrainingSession, TrainingSession.id == Report.session_id)
        .where(_owner_condition(token))
        .order_by(Report.generated_at.desc())
    )
    return row.payload_json if row else None


def _resume_contexts(
    db: Session, token: AuthToken, session_id: str | None
) -> list[dict]:
    if session_id:
        owned_training_session(session_id, db, token)
        materials = list(
            db.scalars(
                select(Material)
                .where(
                    Material.session_id == session_id,
                    Material.material_type == "resume",
                    Material.parse_status == "parsed",
                )
                .order_by(Material.created_at.desc())
            )
        )
    else:
        latest = db.scalar(
            select(Material)
            .join(TrainingSession, TrainingSession.id == Material.session_id)
            .where(
                _owner_condition(token),
                Material.material_type == "resume",
                Material.parse_status == "parsed",
            )
            .order_by(Material.created_at.desc())
        )
        materials = [latest] if latest else []
    return [context for material in materials for context in (material.contexts_json or [])]


@router.post("/profile", response_model=JobCandidateProfile)
def build_profile(
    payload: JobProfileBuildRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> JobCandidateProfile:
    resume_contexts = (
        _resume_contexts(db, token, payload.session_id)
        if payload.source in {"resume", "combined"}
        else []
    )
    report = _recent_report(db, token) if payload.source in {"recent_report", "combined"} else None
    try:
        return CandidateProfileBuilder(request.app.state.ai_provider).build(
            source=payload.source,
            resume_contexts=resume_contexts,
            recent_report=report,
        )
    except ValueError as exc:
        raise api_error(422, "profile_source_unavailable", str(exc)) from exc
    except Exception as exc:
        raise api_error(503, "profile_generation_failed", f"求职画像生成失败：{exc}") from exc


@router.post("/search", response_model=JobRecommendationSearchResponse)
def search_jobs(
    payload: JobRecommendationSearchRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
) -> JobRecommendationSearchResponse:
    del token  # 鉴权依赖本身即为访问控制。
    query = " ".join(
        value for value in (payload.profile.target_position, payload.profile.expected_city) if value
    )
    service = JobRecommendationService(
        job_source=request.app.state.job_source,
        ai_provider=request.app.state.ai_provider,
        seed_source=request.app.state.seed_job_source,
        link_checker=request.app.state.job_link_checker,
    )
    try:
        result = service.recommend_with_metadata(payload.profile)
    except JSearchConfigurationError as exc:
        raise api_error(503, "jsearch_not_configured", str(exc)) from exc
    except JSearchTimeoutError as exc:
        raise api_error(504, "jsearch_timeout", str(exc)) from exc
    except JSearchAPIError as exc:
        raise api_error(502, "jsearch_error", str(exc)) from exc
    except SeedDataError as exc:
        raise api_error(500, "job_seed_data_error", str(exc)) from exc
    except ValueError as exc:
        raise api_error(422, "invalid_job_profile", str(exc)) from exc
    if not result.jobs:
        return JobRecommendationSearchResponse(
            query=query,
            jobs=[],
            match_mode=result.match_mode,
            fallback_reason=result.fallback_reason,
            message="暂未搜索到符合画像的岗位，请调整岗位方向或城市后重试。",
        )
    return JobRecommendationSearchResponse(
        query=query,
        jobs=[JobRecommendationItem.model_validate(item) for item in result.jobs],
        match_mode=result.match_mode,
        fallback_reason=result.fallback_reason,
        message=result.fallback_reason,
    )


@router.post("/interview", response_model=TrainingSessionResponse)
def start_job_interview(
    payload: JobInterviewStartRequest,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> TrainingSessionResponse:
    training = TrainingSession(
        owner_user_id=token.user_id,
        created_by_token_id=token.id,
        mode="job",
        position=payload.job.title,
        company=payload.job.company_name,
        status="created",
    )
    db.add(training)
    db.flush()
    context_text = "\n".join(
        [
            f"岗位：{payload.job.title}",
            f"公司：{payload.job.company_name}",
            f"城市：{payload.job.city}",
            f"技能要求：{'、'.join(payload.job.required_skills)}",
            f"岗位描述：{payload.job.description}",
        ]
    )
    material = Material(
        session_id=training.id,
        material_type="jd",
        original_filename=f"job-{payload.job.job_id}.json",
        storage_path="",
        mime_type="application/json",
        size_bytes=len(context_text.encode("utf-8")),
        parse_status="parsed",
        contexts_json=[
            {
                "chunk_id": f"job-{payload.job.job_id}",
                "source_type": "jd",
                "text": context_text,
                "metadata": {
                    "provider": payload.job.data_source,
                    "apply_link": payload.job.apply_link,
                    "candidate_profile": payload.profile.model_dump(mode="json"),
                },
            }
        ],
    )
    db.add(material)
    db.commit()
    db.refresh(training)
    return TrainingSessionResponse(
        session_id=training.id,
        mode=training.mode,
        position=training.position,
        company=training.company,
        learning_module=training.learning_module,
        learning_module_title=training.learning_module_title,
        question_mix=training.question_mix,
        status=training.status,
        created_at=training.created_at,
    )
