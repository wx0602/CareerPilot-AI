from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from knowledge.models import MATERIAL_TYPES, MATERIAL_TYPE_ALIASES, ParsedMaterial

from .jd_parser import parse_jd_text
from .resume_parser import parse_resume_text
from .text_extractors import extract_text


class DocumentParseError(ValueError):
    pass


def parse_material(
    path: str | Path,
    *,
    material_type: str,
    user_id: str = "guest",
    material_id: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> ParsedMaterial:
    material_type = MATERIAL_TYPE_ALIASES.get(material_type, material_type)
    if material_type not in MATERIAL_TYPES:
        raise DocumentParseError(f"不支持的材料类型: {material_type}")
    source = Path(path)
    try:
        text = extract_text(source)
    except (OSError, RuntimeError, ValueError) as exc:
        raise DocumentParseError(str(exc)) from exc

    structured: dict[str, Any] = {}
    if material_type == "resume":
        structured = parse_resume_text(text)
    elif material_type == "jd":
        structured = parse_jd_text(text)
    elif material_type == "pitch_ppt":
        structured = {"slide_count": text.count("[第"), "summary_source": "extracted_text"}

    generated_id = material_id or hashlib.sha256(
        f"{user_id}:{material_type}:{source.name}:{text}".encode("utf-8")
    ).hexdigest()[:20]
    metadata = {
        "source": str(source.resolve()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "extension": source.suffix.lower(),
        "character_count": len(text),
    }
    metadata.update(extra_metadata or {})
    return ParsedMaterial(
        material_id=generated_id,
        user_id=user_id,
        type=material_type,
        filename=source.name,
        parsed_text=text,
        metadata=metadata,
        structured_data=structured,
    )
