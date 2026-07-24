from contextlib import asynccontextmanager
from pathlib import Path
from re import compile as compile_pattern
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from .api.routes import auth, exams, favorites, interviews, job_recommendations, materials, reports, simulations, training_sessions
from .core.config import Settings, get_settings
from .core.logging import bind_request_id, configure_logging, reset_request_id
from .db.session import create_database_engine, create_session_factory
from .services.auth import ensure_demo_user
from .services.providers import AIProvider, KnowledgeProvider, build_providers
from .services.job_recommendations import JobLinkChecker, JSearchJobSource, SeedJobSource


REQUEST_ID_PATTERN = compile_pattern(r"^[A-Za-z0-9._-]{1,64}$")


def _request_id(value: str | None) -> str:
    return value if value and REQUEST_ID_PATTERN.fullmatch(value) else uuid4().hex


def create_app(
    settings: Settings | None = None,
    knowledge_provider: KnowledgeProvider | None = None,
    ai_provider: AIProvider | None = None,
    job_source: JSearchJobSource | None = None,
    seed_job_source: SeedJobSource | None = None,
    job_link_checker: JobLinkChecker | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    logger = configure_logging(app_settings)
    engine = create_database_engine(
        app_settings.database_url,
        sqlite_busy_timeout_ms=app_settings.database_busy_timeout_ms,
        slow_query_ms=app_settings.slow_query_ms,
    )
    session_factory = create_session_factory(engine)
    if knowledge_provider is None or ai_provider is None:
        default_knowledge, default_ai = build_providers(app_settings.provider_mode)
        knowledge_provider = knowledge_provider or default_knowledge
        ai_provider = ai_provider or default_ai
    job_source = job_source or JSearchJobSource(
        api_key=app_settings.jsearch_api_key,
        base_url=app_settings.jsearch_base_url,
        timeout_seconds=app_settings.jsearch_timeout_seconds,
    )
    seed_job_source = seed_job_source or SeedJobSource()
    job_link_checker = job_link_checker or JobLinkChecker()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        logger.info(
            "应用开始启动",
            extra={"event": "application_starting", "provider_mode": app_settings.provider_mode},
        )
        Path(app_settings.upload_dir).mkdir(parents=True, exist_ok=True)
        if not inspect(engine).has_table("users"):
            logger.error("数据库尚未迁移", extra={"event": "database_not_migrated"})
            raise RuntimeError("数据库尚未迁移，请先运行：alembic upgrade head")
        with session_factory() as db:
            ensure_demo_user(db, app_settings)
        logger.info("应用启动完成", extra={"event": "application_started"})
        try:
            yield
        finally:
            engine.dispose()
            logger.info("应用已停止", extra={"event": "application_stopped"})

    application = FastAPI(
        title=app_settings.app_name,
        description="CareerPilot AI 第一阶段后端服务（B 工作区）",
        version="0.2.0",
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.knowledge_provider = knowledge_provider
    application.state.ai_provider = ai_provider
    application.state.job_source = job_source
    application.state.seed_job_source = seed_job_source
    application.state.job_link_checker = job_link_checker
    application.state.logger = logger

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_origin_regex=app_settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = _request_id(request.headers.get("X-Request-ID"))
        token = bind_request_id(request_id)
        request.state.request_id = request_id
        started_at = perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (perf_counter() - started_at) * 1000
            response.headers["X-Request-ID"] = request_id
            log_method = logger.warning if (
                response.status_code >= 400
                or (
                    app_settings.slow_request_ms > 0
                    and duration_ms >= app_settings.slow_request_ms
                )
            ) else logger.info
            log_method(
                "HTTP 请求完成",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            return response
        except Exception:
            logger.exception(
                "HTTP 请求处理失败",
                extra={
                    "event": "http_request_failed",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                },
            )
            raise
        finally:
            reset_request_id(token)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "validation_error",
                    "message": "请求参数不正确",
                }
            },
        )

    @application.exception_handler(SQLAlchemyError)
    async def database_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error(
            "数据库操作失败",
            extra={
                "event": "database_error",
                "path": request.url.path,
                "error_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "database_unavailable",
                    "message": "数据库暂时不可用，请稍后重试",
                }
            },
        )

    @application.get("/")
    def root():
        return {"message": "CareerPilot AI API is running", "docs": "/docs"}

    @application.get("/health", tags=["系统"])
    def health_check():
        with session_factory() as db:
            db.execute(text("SELECT 1"))
            migration_revision = None
            if inspect(engine).has_table("alembic_version"):
                migration_revision = db.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).scalar_one_or_none()
            database = {
                "status": "ok",
                "dialect": engine.dialect.name,
                "migration_revision": migration_revision,
            }
            if engine.dialect.name == "sqlite":
                database["foreign_keys"] = bool(db.execute(text("PRAGMA foreign_keys")).scalar())
                database["journal_mode"] = db.execute(text("PRAGMA journal_mode")).scalar()
        return {
            "status": "ok",
            "service": app_settings.app_name,
            "provider_mode": app_settings.provider_mode,
            "database": database,
        }

    for router in (
        auth.router,
        training_sessions.router,
        materials.router,
        exams.router,
        favorites.router,
        job_recommendations.router,
        interviews.router,
        simulations.router,
        reports.router,
    ):
        application.include_router(router, prefix="/api")

    return application


app = create_app()
