from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.orm import Session

from ..deps import get_current_token, get_db, owned_training_session
from ...core.errors import api_error
from ...dbmodels import AuthToken, Material
from ...schemas.api import MaterialUploadResponse
from ...services.providers import ProviderUnavailableError


router = APIRouter(prefix="/materials", tags=["材料"])
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".pptx"}
MATERIAL_TYPES = {"resume", "jd", "business_plan", "pitch_ppt", "project_intro"}


def _valid_signature(path: Path, extension: str) -> bool:
    head = path.read_bytes()[:16]
    if extension == ".pdf":
        return head.startswith(b"%PDF-")
    if extension == ".doc":
        return head.startswith(bytes.fromhex("D0CF11E0A1B11AE1"))
    if extension == ".docx":
        try:
            with ZipFile(path) as archive:
                names = archive.namelist()
                return "[Content_Types].xml" in names and any(name.startswith("word/") for name in names)
        except BadZipFile:
            return False
    if extension == ".pptx":
        try:
            with ZipFile(path) as archive:
                names = archive.namelist()
                return "[Content_Types].xml" in names and any(name.startswith("ppt/") for name in names)
        except BadZipFile:
            return False
    if extension == ".txt":
        try:
            path.read_text(encoding="utf-8")
            return b"\x00" not in head
        except UnicodeDecodeError:
            return False
    return False


@router.post("/upload", response_model=MaterialUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_material(
    request: Request,
    session_id: str = Form(...),
    material_type: str = Form(...),
    file: UploadFile = File(...),
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> MaterialUploadResponse:
    owned_training_session(session_id, db, token)
    if material_type not in MATERIAL_TYPES:
        raise api_error(422, "unsupported_material_type", "不支持该材料类型")
    original_name = Path(file.filename or "").name
    extension = Path(original_name).suffix.lower()
    if not original_name or extension not in ALLOWED_EXTENSIONS:
        raise api_error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "unsupported_file_type", "仅支持 PDF、DOC、DOCX、TXT、PPTX")

    upload_dir = Path(request.app.state.settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{uuid4()}{extension}"
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > request.app.state.settings.max_upload_bytes:
                    raise api_error(
                        status.HTTP_413_CONTENT_TOO_LARGE,
                        "file_too_large",
                        "文件大小不能超过 10MB",
                    )
                output.write(chunk)
        if not _valid_signature(destination, extension):
            raise api_error(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "invalid_file_content",
                "文件内容与扩展名不匹配或文件已损坏",
            )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()

    material = Material(
        session_id=session_id,
        material_type=material_type,
        original_filename=original_name,
        storage_path=str(destination),
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        parse_status="pending",
        contexts_json=[],
    )
    db.add(material)
    db.flush()
    try:
        contexts = request.app.state.knowledge_provider.parse_material(destination, material_type)
        material.contexts_json = contexts
        material.parse_status = "parsed"
    except ProviderUnavailableError as exc:
        material.parse_status = "failed"
        material.parse_error = str(exc)
    except Exception:
        material.parse_status = "failed"
        material.parse_error = "材料解析失败"
    db.commit()
    db.refresh(material)
    return MaterialUploadResponse(
        material_id=material.id,
        session_id=material.session_id,
        material_type=material.material_type,
        filename=material.original_filename,
        mime_type=material.mime_type,
        size_bytes=material.size_bytes,
        parse_status=material.parse_status,
        parse_error=material.parse_error,
        created_at=material.created_at,
    )
