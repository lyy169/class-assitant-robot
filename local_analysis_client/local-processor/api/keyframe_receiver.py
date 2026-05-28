from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from yolo_interaction_processor import build_default_processor, configure_logging, load_raw_config, resolve_config_path


CONFIG_PATH = resolve_config_path()
configure_logging(CONFIG_PATH)
LOGGER = logging.getLogger("keyframe_receiver")

RAW_CONFIG = load_raw_config(CONFIG_PATH)
SERVER_CONFIG = RAW_CONFIG.get("server", {})
PROCESSOR = build_default_processor(CONFIG_PATH)
RECEIVED_DIR = PROCESSOR.config.received_keyframes_dir
RECEIVED_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title=SERVER_CONFIG.get("title", "YOLO Keyframe Receiver"),
    version=SERVER_CONFIG.get("version", "2.0.0"),
)


@app.get("/health")
async def health() -> dict[str, Any]:
    """健康检查接口。"""
    return {
        "status": "ok",
        "time": datetime.now().isoformat(timespec="seconds"),
        "config_path": str(CONFIG_PATH),
        "use_merged_model": PROCESSOR.config.use_merged_model,
        "merged_model_path": str(PROCESSOR.config.merged_model_path) if PROCESSOR.config.merged_model_path else None,
    }


@app.post("/api/keyframes")
async def receive_keyframes(
    window_id: str = Form(...),
    timestamp: str = Form(...),
    device_id: str | None = Form(None),
    classroom_id: str | None = Form(None),
    frame_timestamps: str | None = Form(None),
    metadata_json: str | None = Form(None),
    images: list[UploadFile] = File(...),
) -> JSONResponse:
    """接收树莓派上传的关键帧窗口。"""
    if not images:
        raise HTTPException(status_code=400, detail="images 不能为空")

    window_dir = _build_window_dir(RECEIVED_DIR, window_id, timestamp)
    window_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("开始接收关键帧: window_id=%s image_count=%s", window_id, len(images))

    saved_paths: list[str] = []
    for index, upload in enumerate(images):
        try:
            if not upload.content_type or "jpeg" not in upload.content_type.lower():
                LOGGER.warning("收到非标准 JPEG 类型文件: filename=%s content_type=%s", upload.filename, upload.content_type)

            file_name = upload.filename or f"frame_{index:03d}.jpg"
            if not file_name.lower().endswith((".jpg", ".jpeg")):
                file_name = f"{Path(file_name).stem}.jpg"

            target_path = window_dir / f"{index:03d}_{file_name}"
            content = await upload.read()
            target_path.write_bytes(content)
            saved_paths.append(str(target_path))
        except Exception:
            LOGGER.exception("保存上传图片失败: window_id=%s index=%s filename=%s", window_id, index, upload.filename)
            raise HTTPException(status_code=500, detail=f"保存图片失败: {upload.filename}")

    parsed_frame_timestamps = _parse_json_list(frame_timestamps, "frame_timestamps")
    extra_metadata = _parse_json_object(metadata_json, "metadata_json")
    extra_metadata["device_id"] = device_id
    extra_metadata["classroom_id"] = classroom_id
    extra_metadata["received_dir"] = str(window_dir)
    extra_metadata.setdefault("source_host", device_id or PROCESSOR.config.source_host)
    extra_metadata["local_processor_host"] = PROCESSOR.config.source_host

    request_snapshot = {
        "window_id": window_id,
        "timestamp": timestamp,
        "device_id": device_id,
        "classroom_id": classroom_id,
        "frame_timestamps": parsed_frame_timestamps,
        "image_count": len(saved_paths),
        "saved_paths": saved_paths,
        "received_dir": str(window_dir),
        "source_host": extra_metadata.get("source_host"),
        "local_processor_host": PROCESSOR.config.source_host,
        "received_at": datetime.now().isoformat(timespec="seconds"),
    }
    (window_dir / "request_meta.json").write_text(json.dumps(request_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        result = PROCESSOR.process_window(
            window_id=window_id,
            frame_paths=saved_paths,
            window_timestamp=timestamp,
            frame_timestamps=parsed_frame_timestamps,
            metadata=extra_metadata,
        )
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("窗口处理失败: window_id=%s", window_id)
        raise HTTPException(status_code=500, detail=f"window processing failed: {exc}") from exc

    return JSONResponse(
        content={
            "status": "success",
            "schema_version": result.get("schema_version"),
            "window_id": window_id,
            "saved_count": len(saved_paths),
            "received_dir": str(window_dir),
            "summary": result["summary"],
            "result_path": str(PROCESSOR.config.output_dir / f"{window_id}.json"),
        }
    )


def _parse_json_list(value: str | None, field_name: str) -> list[Any]:
    """解析 JSON 数组字符串。"""
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 不是合法 JSON: {exc}") from exc
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail=f"{field_name} 必须是 JSON 数组")
    return parsed


def _parse_json_object(value: str | None, field_name: str) -> dict[str, Any]:
    """解析 JSON 对象字符串。"""
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 不是合法 JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail=f"{field_name} 必须是 JSON 对象")
    return parsed


def _build_window_dir(base_dir: Path, window_id: str, timestamp: str | None) -> Path:
    """按日期时间组织关键帧目录，便于检索和回溯。"""
    dt = _parse_storage_datetime(timestamp) or datetime.now()
    date_dir = dt.strftime("%Y-%m-%d")
    time_dir = f"{dt.strftime('%H%M%S')}_{_sanitize_path_part(window_id)}"
    return base_dir / date_dir / time_dir


def _parse_storage_datetime(value: str | None) -> datetime | None:
    """解析用于目录分组的窗口时间。"""
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return datetime.fromtimestamp(float(text))
    except ValueError:
        pass

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        LOGGER.warning("窗口时间格式无法用于目录分组，已回退到当前时间: %s", value)
        return None


def _sanitize_path_part(value: str) -> str:
    """清洗路径片段，避免非法文件名字符。"""
    sanitized = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value.strip())
    return sanitized or "window"


def main() -> None:
    """兼容根目录入口的启动函数。"""
    uvicorn.run(
        "keyframe_receiver:app",
        host=SERVER_CONFIG.get("host", "0.0.0.0"),
        port=int(SERVER_CONFIG.get("port", 8000)),
        reload=False,
    )


if __name__ == "__main__":
    main()
