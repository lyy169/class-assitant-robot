"""课堂交互分析系统云端接收服务入口。"""
from __future__ import annotations

import html
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .auth import router as auth_router
from .admin_pages import (
    build_admin_classrooms_html,
    build_admin_home_html,
    build_admin_ingestion_html,
    build_admin_results_html,
    build_admin_teachers_html,
)
from .dashboard_v11 import build_results_center_html, latest_result_or_404
from .logging_utils import setup_logging
from .schemas_v11 import ApiResponse, InteractionResultPayload
from .storage import FileResultRepository, build_query_repository
from .teacher_pages import build_teacher_home_html, build_teacher_results_html


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


def _mount_video_uploads() -> None:
    """Expose demo videos when the runtime upload directory exists."""
    candidates = [settings.video_upload_dir, Path("/root/video_project/upload")]
    supported_suffixes = {".mp4", ".webm", ".mov", ".ogg"}
    video_dirs = [
        candidate
        for candidate in candidates
        if candidate.exists()
        and candidate.is_dir()
        and (
            (candidate / "video.mp4").exists()
            or any(path.is_file() and path.suffix.lower() in supported_suffixes for path in candidate.iterdir())
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


@app.get("/health")
async def health() -> Dict[str, str]:
    """健康检查接口。"""
    return {"status": "ok"}


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
) -> HTMLResponse:
    """Render a teacher-facing classroom results center."""
    if status not in (None, "", "raw", "reviewed", "archived"):
        raise HTTPException(status_code=400, detail="status must be raw, reviewed, or archived")
    payload, source_path, source_kind = latest_result_or_404(repository, classroom_id=classroom_id)
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
        )
    )


@app.get("/teacher", response_class=HTMLResponse)
async def teacher_home() -> HTMLResponse:
    """Render the Phase 2.6 teacher home page."""
    return HTMLResponse(content=build_teacher_home_html())


@app.get("/teacher/results", response_class=HTMLResponse)
async def teacher_results_page() -> HTMLResponse:
    """Render the Phase 2.6 classroom records center."""
    return HTMLResponse(content=build_teacher_results_html())


@app.get("/admin", response_class=HTMLResponse)
async def admin_home() -> HTMLResponse:
    """Render the Phase 2.7 admin platform overview."""
    return HTMLResponse(content=build_admin_home_html())


@app.get("/admin/classrooms", response_class=HTMLResponse)
async def admin_classrooms_page() -> HTMLResponse:
    """Render the Phase 2.7 admin classroom overview."""
    return HTMLResponse(content=build_admin_classrooms_html())


@app.get("/admin/teachers", response_class=HTMLResponse)
async def admin_teachers_page() -> HTMLResponse:
    """Render the Phase 2.7 admin teacher overview."""
    return HTMLResponse(content=build_admin_teachers_html())


@app.get("/admin/results", response_class=HTMLResponse)
async def admin_results_page() -> HTMLResponse:
    """Render the Phase 2.7 all-platform classroom results view."""
    return HTMLResponse(content=build_admin_results_html())


@app.get("/admin/ingestion", response_class=HTMLResponse)
async def admin_ingestion_page() -> HTMLResponse:
    """Render the Phase 2.8 three-side ingestion status view."""
    return HTMLResponse(content=build_admin_ingestion_html())


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

    return ApiResponse(
        success=True,
        message="课堂交互结果接收成功",
        request_id=request_id,
        saved_path=str(saved_path),
    )


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
