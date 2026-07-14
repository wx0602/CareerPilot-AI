from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover - 依赖缺失时给出明确错误
    HumanMessage = None
    SystemMessage = None
    ChatOpenAI = None


T = TypeVar("T", bound=BaseModel)

AI_CORE_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = AI_CORE_ROOT / ".env"
PROMPT_ROOT = AI_CORE_ROOT / "prompts"


class LLMError(RuntimeError):
    pass


def _load_env_file() -> None:
    # 只读取 ai-core/.env，不打印、不修改任何密钥值。
    if not ENV_PATH.exists():
        return

    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_prompt(name: str) -> str:
    return (PROMPT_ROOT / name).read_text(encoding="utf-8")


def _require_config() -> tuple[str, str, str]:
    _load_env_file()
    api_key = os.environ.get("LLM_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL")
    model = os.environ.get("LLM_MODEL")
    missing = [
        name
        for name, value in {
            "LLM_API_KEY": api_key,
            "LLM_BASE_URL": base_url,
            "LLM_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        raise LLMError(f"缺少大模型配置：{', '.join(missing)}")
    return api_key, base_url.rstrip("/"), model


def _chat_base_url(base_url: str) -> str:
    # ChatOpenAI 需要 OpenAI-compatible base_url，去掉完整接口路径。
    if base_url.endswith("/chat/completions"):
        return base_url[: -len("/chat/completions")]
    if base_url.endswith("/v1"):
        return base_url
    # 兼容 .env 中只配置供应商根地址的情况。
    return f"{base_url}/v1"


def _extract_json(text: str) -> dict[str, Any]:
    # DeepSeek 通常会遵守 response_format；这里额外处理代码块或多余文本，
    # 确保后续仍能进入 JSON 解析和 Pydantic 校验。
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.S)
    if fenced:
        cleaned = fenced.group(1).strip()
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= start:
            cleaned = cleaned[start : end + 1]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError(f"大模型返回内容不是合法 JSON：{exc}") from exc
    if not isinstance(data, dict):
        raise LLMError("大模型返回 JSON 必须是对象")
    return data


def _build_chat_model(*, temperature: float) -> Any:
    if ChatOpenAI is None:
        raise LLMError("缺少 LangChain 依赖，请先安装 ai-core/requirements.txt。")

    api_key, base_url, model = _require_config()
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=_chat_base_url(base_url),
        temperature=temperature,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def call_json_model(
    *,
    system_prompt: str,
    user_payload: dict[str, Any],
    response_model: type[T],
    temperature: float = 0.2,
    max_retries: int = 2,
) -> T:
    # 统一的大模型调用边界：LangChain 调用、JSON 解析、重试和 Pydantic 校验都在这里完成。
    chat = _build_chat_model(temperature=temperature)
    messages: list[Any] = [
        SystemMessage(
            content=(
                system_prompt
                + "\n\n必须只输出一个合法 JSON 对象，不要输出 Markdown、解释或多余文本。"
            )
        ),
        HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
    ]
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = chat.invoke(messages)
            parsed = _extract_json(str(response.content))
            return response_model.model_validate(parsed)
        except (KeyError, json.JSONDecodeError, ValidationError, LLMError) as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            # 把校验失败原因反馈给模型，让它按同一 schema 重新输出。
            # max_retries=2 表示最多进行两次修复重试。
            messages.append(
                HumanMessage(
                    content=(
                        "上一次输出未通过 JSON 或 Pydantic 校验，"
                        f"错误：{exc}。请严格按目标字段重新输出一个合法 JSON 对象。"
                    )
                )
            )

    raise LLMError(f"大模型 JSON 输出连续校验失败：{last_error}")


def to_jsonable(model_or_value: Any) -> Any:
    # 递归转换 Pydantic 对象，避免请求 payload 中混入不可 JSON 序列化的数据。
    if isinstance(model_or_value, BaseModel):
        return model_or_value.model_dump(mode="json")
    if isinstance(model_or_value, list):
        return [to_jsonable(item) for item in model_or_value]
    if isinstance(model_or_value, dict):
        return {key: to_jsonable(value) for key, value in model_or_value.items()}
    return model_or_value
