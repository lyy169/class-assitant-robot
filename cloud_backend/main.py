"""课堂交互分析系统云端接收服务入口。"""
from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import settings
from .logging_utils import setup_logging
from .schemas import ApiResponse, InteractionResultPayload
from .storage import FileResultRepository


logger = setup_logging(settings.log_level)
repository = FileResultRepository(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用启动和关闭逻辑。"""
    settings.ensure_directories()
    logger.info("云端接收服务启动完成，数据目录：%s", settings.data_dir)
    yield
    logger.info("云端接收服务已关闭")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="用于接收本地课堂交互分析结果并落盘/入库的云端服务",
    lifespan=lifespan,
)


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
    if settings.source_host_required and not payload.source_host:
        raise HTTPException(status_code=422, detail="source_host 为必填字段")


@app.get("/health")
async def health() -> Dict[str, str]:
    """健康检查接口。"""
    return {"status": "ok"}


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

    saved_path = repository.save(payload.model_dump(mode="json"))

    logger.info(
        "接收到课堂交互结果 | request_id=%s | client=%s | classroom_id=%s | window_id=%s | saved_path=%s",
        request_id,
        client_host,
        payload.classroom_id,
        payload.window_id,
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
