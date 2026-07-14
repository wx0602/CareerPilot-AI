from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from .api.routes import auth, exams, favorites, interviews, materials, reports, training_sessions
from .core.config import Settings, get_settings
from .db.session import create_database_engine, create_session_factory
from .services.auth import ensure_demo_user
from .services.providers import AIProvider, KnowledgeProvider, build_providers


def create_app(
    settings: Settings | None = None,
    knowledge_provider: KnowledgeProvider | None = None,
    ai_provider: AIProvider | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    engine = create_database_engine(app_settings.database_url)
    session_factory = create_session_factory(engine)
    if knowledge_provider is None or ai_provider is None:
        default_knowledge, default_ai = build_providers(app_settings.provider_mode)
        knowledge_provider = knowledge_provider or default_knowledge
        ai_provider = ai_provider or default_ai

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        Path(app_settings.upload_dir).mkdir(parents=True, exist_ok=True)
        if not inspect(engine).has_table("users"):
            raise RuntimeError("数据库尚未迁移，请先运行：alembic upgrade head")
        with session_factory() as db:
            ensure_demo_user(db, app_settings)
        yield
        engine.dispose()

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

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list,
        allow_origin_regex=app_settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    @application.get("/")
    def root():
        return {"message": "CareerPilot AI API is running", "docs": "/docs"}

    @application.get("/health", tags=["系统"])
    def health_check():
        with session_factory() as db:
            db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "service": app_settings.app_name,
            "provider_mode": app_settings.provider_mode,
        }

    for router in (
        auth.router,
        training_sessions.router,
        materials.router,
        exams.router,
        favorites.router,
        interviews.router,
        reports.router,
    ):
        application.include_router(router, prefix="/api")

    return application


app = create_app()
