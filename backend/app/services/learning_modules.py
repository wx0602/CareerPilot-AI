from __future__ import annotations

from dataclasses import dataclass

from app.schemas.api import QuestionMix


@dataclass(frozen=True)
class LearningModuleSpec:
    module_id: str
    title: str
    category: str
    default_position: str
    search_position: str | None = None
    search_knowledge_points: tuple[str, ...] = ()
    available: bool = True


DEFAULT_QUESTION_MIX = QuestionMix()


LEARNING_MODULES: dict[str, LearningModuleSpec] = {
    "java_backend": LearningModuleSpec(
        module_id="java_backend",
        title="Java 后端",
        category="后端基础",
        default_position="Java 后端工程师",
        search_position="java_backend",
    ),
    "python_backend": LearningModuleSpec(
        module_id="python_backend",
        title="Python 后端",
        category="后端基础",
        default_position="Python 后端工程师",
        search_position="python_backend",
    ),
    "frontend_javascript": LearningModuleSpec(
        module_id="frontend_javascript",
        title="JavaScript",
        category="前端基础",
        default_position="前端工程师",
        search_position="frontend_javascript",
        available=False,
    ),
    "frontend_typescript": LearningModuleSpec(
        module_id="frontend_typescript",
        title="TypeScript",
        category="前端基础",
        default_position="前端工程师",
        search_position="frontend_typescript",
        available=False,
    ),
    "frontend_vue": LearningModuleSpec(
        module_id="frontend_vue",
        title="Vue",
        category="前端基础",
        default_position="前端工程师",
        search_position="frontend_vue",
        available=False,
    ),
    "browser_principles": LearningModuleSpec(
        module_id="browser_principles",
        title="浏览器原理",
        category="前端基础",
        default_position="前端工程师",
        search_position="browser_principles",
        available=False,
    ),
    "go_backend": LearningModuleSpec(
        module_id="go_backend",
        title="Go 后端",
        category="语言方向",
        default_position="Go 后端工程师",
        search_position="go_backend",
        available=False,
    ),
    "cpp_basic": LearningModuleSpec(
        module_id="cpp_basic",
        title="C++ 基础",
        category="语言方向",
        default_position="C++ 工程师",
        search_position="cpp_basic",
        available=False,
    ),
    "ai_llm_engineering": LearningModuleSpec(
        module_id="ai_llm_engineering",
        title="AI / LLM 工程",
        category="AI 方向",
        default_position="AI 工程师",
        search_position="ai_llm_engineering",
        available=False,
    ),
    "product_manager": LearningModuleSpec(
        module_id="product_manager",
        title="产品",
        category="通用岗位",
        default_position="产品经理",
        search_position="product_manager",
        available=False,
    ),
    "testing_engineering": LearningModuleSpec(
        module_id="testing_engineering",
        title="测试",
        category="通用岗位",
        default_position="测试工程师",
        search_position="testing_engineering",
        available=False,
    ),
    "devops_engineering": LearningModuleSpec(
        module_id="devops_engineering",
        title="运维",
        category="通用岗位",
        default_position="运维工程师",
        search_position="devops_engineering",
        available=False,
    ),
}


def get_learning_module(module_id: str | None) -> LearningModuleSpec | None:
    if not module_id:
        return None
    return LEARNING_MODULES.get(module_id)


def default_question_mix() -> QuestionMix:
    return QuestionMix.model_validate(DEFAULT_QUESTION_MIX.model_dump())
