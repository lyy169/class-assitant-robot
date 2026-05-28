"""课堂交互分析系统云端接收服务入口。"""
from __future__ import annotations

import html
import json
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Cookie, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .auth import AUTH_COOKIE_NAME, optional_page_user, require_page_user, router as auth_router
from .admin_pages import (
    build_admin_classrooms_html,
    build_admin_home_html,
    build_admin_ingestion_html,
    build_admin_results_html,
    build_admin_teachers_html,
)
from .dashboard_v11 import build_results_center_html, latest_result_or_404
from .login_pages import build_forbidden_html, build_login_html, build_register_html
from .logging_utils import setup_logging
from .schemas_v11 import ApiResponse, InteractionResultPayload
from .storage import FileResultRepository, build_query_repository
from .teacher_pages import build_teacher_home_html, build_teacher_reports_html, build_teacher_results_html


logger = setup_logging(settings.log_level)
raw_repository = FileResultRepository(settings)
repository = build_query_repository(settings, raw_repository)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用启动和关闭逻辑。"""
    settings.ensure_directories()
    logger.info("Cloud query repository backend=%s", getattr(repository, "backend_name", "unknown"))
    logger.info("云端接收服务启动完成，数据目录：%s", settings.data_dir)
    yield
    logger.info("云端接收服务已关闭")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="用于接收本地课堂交互分析结果并落盘/入库的云端服务",
    lifespan=lifespan,
)
app.include_router(auth_router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), check_dir=False), name="static")

SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".ogg"}


def _mount_video_uploads() -> None:
    """Expose demo videos when the runtime upload directory exists."""
    try:
        settings.video_upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Video uploads directory cannot be created: %s | error=%s", settings.video_upload_dir, exc)
    candidates = [settings.video_upload_dir, Path("/root/video_project/upload")]
    video_dirs = [
        candidate
        for candidate in candidates
        if candidate.exists()
        and candidate.is_dir()
        and (
            (candidate / "video.mp4").exists()
            or any(path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_SUFFIXES for path in candidate.iterdir())
        )
    ]
    for candidate in video_dirs or candidates:
        if candidate.exists() and candidate.is_dir():
            app.mount("/uploads", StaticFiles(directory=str(candidate)), name="uploads")
            logger.info("Mounted video uploads directory at /uploads: %s", candidate)
            return
    logger.warning("Video uploads directory not found; /uploads static route is disabled")


_mount_video_uploads()


def _extract_payload_dict(body: Any) -> Dict[str, Any]:
    """兼容直接 payload 和 envelope 两种提交格式。"""
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")

    if "payload" in body and isinstance(body["payload"], dict):
        return body["payload"]
    return body


def _check_api_key(api_key: Optional[str]) -> None:
    """API Key 简单校验。"""
    if not settings.require_api_key:
        return

    if not api_key:
        raise HTTPException(status_code=401, detail="缺少鉴权请求头：{0}".format(settings.api_key_header))
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="API Key 无效")


def _validate_business_fields(payload: InteractionResultPayload) -> None:
    """业务字段校验。"""
    if settings.classroom_id_required and not payload.classroom_id:
        raise HTTPException(status_code=422, detail="classroom_id 为必填字段")
    if settings.source_host_required and not payload.source.source_host:
        raise HTTPException(status_code=422, detail="source_host 为必填字段")


def _store_validated_payload(
    payload_dict: Dict[str, Any],
    request_id: str,
    client_host: str,
) -> tuple[InteractionResultPayload, Path]:
    """Validate, raw-persist, and index a classroom analysis payload."""
    payload = InteractionResultPayload.model_validate(payload_dict)
    _validate_business_fields(payload)

    payload_dict_for_storage = payload.model_dump(mode="json")
    saved_path = raw_repository.save(payload_dict_for_storage)

    if repository is not raw_repository:
        try:
            repository.save(payload_dict_for_storage, source_path=saved_path, source_kind="raw")
        except Exception as exc:  # pragma: no cover - keep raw persistence as the hard floor
            logger.exception("Query repository indexing failed after raw persistence | request_id=%s | error=%s", request_id, exc)

    logger.info(
        "接收到课堂交互结果 | request_id=%s | client=%s | classroom_id=%s | window_id=%s | saved_path=%s",
        request_id,
        client_host,
        payload.classroom_id,
        payload.analysis_id,
        saved_path,
    )

    return payload, saved_path


def _safe_name_token(value: str, fallback: str = "upload") -> str:
    """Return a path-safe token without trusting client-provided paths."""
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._-")
    return token or fallback


def _safe_upload_filename(filename: Optional[str]) -> str:
    """Normalize an uploaded video filename and reject unsafe suffixes."""
    original_name = Path(filename or "classroom-video.mp4").name
    original_path = Path(original_name)
    suffix = original_path.suffix.lower()
    if suffix not in SUPPORTED_VIDEO_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 mp4/webm/mov/ogg 视频文件")
    stem = _safe_name_token(original_path.stem, fallback="classroom-video")
    return f"{stem}{suffix}"


def _unique_video_path(upload_dir: Path, analysis_id: str, safe_filename: str) -> Path:
    """Build a non-overwriting video path under the configured upload directory."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(safe_filename).suffix.lower()
    stem = Path(safe_filename).stem
    analysis_token = _safe_name_token(analysis_id, fallback="analysis")
    base_name = f"{analysis_token}__{stem}{suffix}"
    candidate = upload_dir / base_name
    if candidate.exists():
        candidate = upload_dir / f"{analysis_token}__{stem}__{uuid.uuid4().hex[:8]}{suffix}"

    resolved_dir = upload_dir.resolve()
    resolved_parent = candidate.parent.resolve()
    if resolved_parent != resolved_dir:
        raise HTTPException(status_code=400, detail="视频文件名不合法")
    return candidate


async def _save_video_upload(video_file: UploadFile, analysis_id: str) -> tuple[Path, str]:
    """Save an uploaded classroom video and return its local path plus /uploads URL."""
    safe_filename = _safe_upload_filename(video_file.filename)
    target_path = _unique_video_path(settings.video_upload_dir, analysis_id, safe_filename)
    try:
        with target_path.open("wb") as file_obj:
            while True:
                chunk = await video_file.read(1024 * 1024)
                if not chunk:
                    break
                file_obj.write(chunk)
    except OSError as exc:
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="视频文件保存失败") from exc

    if not target_path.exists() or target_path.stat().st_size <= 0:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="上传视频文件为空")

    return target_path, f"/uploads/{target_path.name}"


async def _read_result_json_from_form(request: Request, fallback_text: Optional[str]) -> Dict[str, Any]:
    """Read result_json from multipart as either a file field or a string field."""
    form = await request.form()
    result_json_part = form.get("result_json")

    if hasattr(result_json_part, "read"):
        raw_bytes = await result_json_part.read()
        raw_text = raw_bytes.decode("utf-8-sig")
    elif isinstance(result_json_part, str):
        raw_text = result_json_part
    elif fallback_text:
        raw_text = fallback_text
    else:
        raise HTTPException(status_code=400, detail="缺少 result_json 表单字段")

    try:
        body = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="result_json 不是合法 JSON") from exc

    return _extract_payload_dict(body)


def _payload_with_video_url(payload_dict: Dict[str, Any], video_url: str) -> Dict[str, Any]:
    """Inject the cloud video URL while preserving existing video metadata."""
    updated_payload = dict(payload_dict)
    video_info = dict(updated_payload.get("video") or {})
    video_info["video_url"] = video_url
    updated_payload["video"] = video_info
    return updated_payload


@app.get("/health")
async def health() -> Dict[str, str]:
    """健康检查接口。"""
    return {"status": "ok"}


def _login_redirect() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=302)


def _forbidden_response() -> HTMLResponse:
    return HTMLResponse(content=build_forbidden_html(), status_code=403)


def _authorized_classroom_ids(user: Dict[str, Any]) -> Optional[set[str]]:
    if user.get("role") == "admin":
        return None
    if not hasattr(repository, "get_workbench_classrooms"):
        return set()
    return {str(item.get("classroom_id")) for item in repository.get_workbench_classrooms(user_id=user.get("user_id")) if item.get("classroom_id")}


def _dashboard_allowed(user: Dict[str, Any], classroom_id: Optional[str], result_id: Optional[str]) -> bool:
    allowed = _authorized_classroom_ids(user)
    if allowed is None:
        return True
    if result_id and hasattr(repository, "get_workbench_result_detail"):
        detail = repository.get_workbench_result_detail(result_id)
        if detail is None:
            return True
        return str(detail.get("classroom_id") or "") in allowed
    if classroom_id:
        return classroom_id in allowed
    return True


@app.get("/")
async def root(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)):
    user = optional_page_user(auth_token)
    if not user:
        return _login_redirect()
    return RedirectResponse(url="/admin" if user.get("role") == "admin" else "/teacher", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)):
    user = optional_page_user(auth_token)
    if user:
        return RedirectResponse(url="/admin" if user.get("role") == "admin" else "/teacher", status_code=302)
    return HTMLResponse(content=build_login_html())


@app.get("/register", response_class=HTMLResponse)
async def register_page(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)):
    user = optional_page_user(auth_token)
    if user:
        return RedirectResponse(url="/admin" if user.get("role") == "admin" else "/teacher", status_code=302)
    return HTMLResponse(content=build_register_html())


@app.get("/api/latest-interaction-result")
async def latest_interaction_result(classroom_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the latest available classroom interaction result."""
    payload, source_path, source_kind = latest_result_or_404(repository, classroom_id=classroom_id)
    return {
        "success": True,
        "source_kind": source_kind,
        "source_path": str(source_path),
        "result": payload,
    }


@app.get("/api/recent-interaction-results")
async def recent_interaction_results(
    limit: int = Query(default=5, ge=1, le=100),
    classroom_id: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Return recent classroom interaction results with optional classroom filtering."""
    if status not in (None, "", "raw", "reviewed", "archived"):
        raise HTTPException(status_code=400, detail="status must be raw, reviewed, or archived")
    results = repository.recent_results(limit=limit, classroom_id=classroom_id, status=status)
    return {
        "success": True,
        "limit": limit,
        "classroom_id": classroom_id,
        "status": status,
        "fallback_to_sample": bool(results and results[0]["source_kind"] == "sample"),
        "results": [
            {
                "source_kind": item["source_kind"],
                "source_path": str(item["source_path"]),
                "summary": item["summary"],
                "result": item["payload"],
            }
            for item in results
        ],
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    classroom_id: Optional[str] = None,
    status: Optional[str] = None,
    result_id: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),
    auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> HTMLResponse:
    """Render a teacher-facing classroom results center."""
    user = optional_page_user(auth_token)
    if not user:
        return _login_redirect()
    if not _dashboard_allowed(user, classroom_id, result_id):
        return _forbidden_response()
    if status not in (None, "", "raw", "reviewed", "archived"):
        raise HTTPException(status_code=400, detail="status must be raw, reviewed, or archived")
    if user.get("role") == "teacher" and not classroom_id:
        if result_id and hasattr(repository, "get_workbench_result_detail"):
            detail = repository.get_workbench_result_detail(result_id)
            classroom_id = (detail or {}).get("classroom_id") or classroom_id
        if not classroom_id:
            allowed = _authorized_classroom_ids(user) or set()
            classroom_id = sorted(allowed)[0] if allowed else classroom_id
    if result_id and hasattr(repository, "detail_result"):
        selected = repository.detail_result(result_id)
        payload, source_path, source_kind = selected if selected is not None else latest_result_or_404(repository, classroom_id=classroom_id)
    else:
        payload, source_path, source_kind = latest_result_or_404(repository, classroom_id=classroom_id)
    if hasattr(repository, "get_workbench_recent"):
        recent_results = repository.get_workbench_recent(
            limit=limit,
            classroom_id=classroom_id,
            status=status,
            user_id=user.get("user_id") if user.get("role") == "teacher" else None,
        )
    else:
        recent_results = repository.recent_results(limit=limit, classroom_id=classroom_id, status=status)
    return HTMLResponse(
        content=build_results_center_html(
            payload,
            source_path,
            source_kind,
            recent_results,
            classroom_id,
            status,
            limit,
            result_id,
            user,
        )
    )


@app.get("/teacher", response_class=HTMLResponse)
async def teacher_home(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> HTMLResponse:
    """Render the Phase 2.6 teacher home page."""
    try:
        user = require_page_user(auth_token, required_role="teacher")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return HTMLResponse(content=build_teacher_home_html(user))


@app.get("/teacher/results", response_class=HTMLResponse)
async def teacher_results_page(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> HTMLResponse:
    """Render the Phase 2.6 classroom records center."""
    try:
        user = require_page_user(auth_token, required_role="teacher")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return HTMLResponse(content=build_teacher_results_html(user))


@app.get("/teacher/trends", response_class=HTMLResponse)
async def teacher_trends_page(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> HTMLResponse:
    """Redirect the retired trend page to the report center."""
    try:
        require_page_user(auth_token, required_role="teacher")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return RedirectResponse(url="/teacher/reports", status_code=302)


@app.get("/teacher/reports", response_class=HTMLResponse)
async def teacher_reports_page(
    result_id: Optional[str] = None,
    auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> HTMLResponse:
    """Render the Phase 3.0 classroom report list or detail page."""
    try:
        user = require_page_user(auth_token, required_role="teacher")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return HTMLResponse(content=build_teacher_reports_html(user, result_id=result_id))


@app.get("/admin", response_class=HTMLResponse)
async def admin_home(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> HTMLResponse:
    """Render the Phase 2.7 admin platform overview."""
    try:
        user = require_page_user(auth_token, required_role="admin")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return HTMLResponse(content=build_admin_home_html(user))


@app.get("/admin/classrooms", response_class=HTMLResponse)
async def admin_classrooms_page(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> HTMLResponse:
    """Render the Phase 2.7 admin classroom overview."""
    try:
        user = require_page_user(auth_token, required_role="admin")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return HTMLResponse(content=build_admin_classrooms_html(user))


@app.get("/admin/teachers", response_class=HTMLResponse)
async def admin_teachers_page(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> HTMLResponse:
    """Render the Phase 2.7 admin teacher overview."""
    try:
        user = require_page_user(auth_token, required_role="admin")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return HTMLResponse(content=build_admin_teachers_html(user))


@app.get("/admin/results", response_class=HTMLResponse)
async def admin_results_page(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> HTMLResponse:
    """Render the Phase 2.7 all-platform classroom results view."""
    try:
        user = require_page_user(auth_token, required_role="admin")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return HTMLResponse(content=build_admin_results_html(user))


@app.get("/admin/ingestion", response_class=HTMLResponse)
async def admin_ingestion_page(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> HTMLResponse:
    """Render the Phase 2.8 three-side ingestion status view."""
    try:
        user = require_page_user(auth_token, required_role="admin")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return HTMLResponse(content=build_admin_ingestion_html(user))


@app.get("/admin/trends", response_class=HTMLResponse)
async def admin_trends_page(auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME)) -> HTMLResponse:
    """Redirect the retired admin trend page to classroom data."""
    try:
        require_page_user(auth_token, required_role="admin")
    except HTTPException as exc:
        return _login_redirect() if exc.status_code == 401 else _forbidden_response()
    return RedirectResponse(url="/admin/results", status_code=302)


@app.post("/api/interaction-results", response_model=ApiResponse)
async def receive_interaction_results(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """接收本地推送的课堂交互统计结果。"""
    request_id = str(uuid.uuid4())
    client_host = request.client.host if request.client else "unknown"

    _check_api_key(x_api_key)

    try:
        body = await request.json()
    except json.JSONDecodeError as exc:
        logger.warning("请求 JSON 解析失败 | request_id=%s | client=%s | error=%s", request_id, client_host, exc)
        raise HTTPException(status_code=400, detail="请求体不是合法 JSON")

    payload_dict = _extract_payload_dict(body)
    _, saved_path = _store_validated_payload(payload_dict, request_id, client_host)

    return ApiResponse(
        success=True,
        message="课堂交互结果接收成功",
        request_id=request_id,
        saved_path=str(saved_path),
    )


@app.post("/api/interaction-results/with-video")
async def receive_interaction_results_with_video(
    request: Request,
    video_file: UploadFile = File(...),
    result_json_text: Optional[str] = Form(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Dict[str, Any]:
    """接收本地端自动上传的课堂视频和分析 JSON 数据包。"""
    request_id = str(uuid.uuid4())
    client_host = request.client.host if request.client else "unknown"

    _check_api_key(x_api_key)

    payload_dict = await _read_result_json_from_form(request, result_json_text)
    prevalidated_payload = InteractionResultPayload.model_validate(payload_dict)
    _validate_business_fields(prevalidated_payload)

    video_path, video_url = await _save_video_upload(video_file, prevalidated_payload.analysis_id)
    payload_with_video = _payload_with_video_url(payload_dict, video_url)
    payload, saved_path = _store_validated_payload(payload_with_video, request_id, client_host)

    return {
        "success": True,
        "message": "课堂视频与分析结果接收成功",
        "request_id": request_id,
        "saved_path": str(saved_path),
        "video_url": video_url,
        "video_path": str(video_path),
        "analysis_id": payload.analysis_id,
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """统一 HTTP 异常响应。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "request_id": str(uuid.uuid4()),
        },
    )
