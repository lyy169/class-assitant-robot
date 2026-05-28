from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_LOCAL_DELIVERY_ROOT = REPO_ROOT / "captures_local_delivery"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "processed_results" / "classroom_feedback"
DEFAULT_PENDING_UPLOAD_DIR = REPO_ROOT / "processed_results" / "phase2_8_1_pending"
UPLOAD_API_PATH = "/api/interaction-results"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consume the latest Raspberry Pi Phase 2.8.1 handoff, analyze, upload, and validate cloud visibility."
    )
    parser.add_argument("--handoff-file", type=Path, required=True, help="SSHFS path to phase2_8_1_latest_session.json.")
    parser.add_argument("--pi-sshfs-root", type=Path, required=True, help="SSHFS root of the Raspberry Pi project.")
    parser.add_argument("--api-base-url", required=True, help="Cloud base URL, for example http://<cloud-host>:8011.")
    parser.add_argument("--local-delivery-root", type=Path, default=DEFAULT_LOCAL_DELIVERY_ROOT)
    parser.add_argument("--config-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pending-upload-dir", type=Path, default=DEFAULT_PENDING_UPLOAD_DIR)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    http_session = _build_http_session()

    markers: dict[str, str] = {
        "PHASE281_LOCAL_OK": "false",
        "PHASE281_HANDOFF_LOADED": "false",
        "PHASE281_REMOTE_SESSION_FOUND": "false",
        "PHASE281_SESSION_COPIED": "false",
        "PHASE281_ANALYSIS_OK": "false",
        "PHASE281_RESULT_JSON": "",
        "PHASE281_RESULT_JSON_VALID": "false",
        "PHASE281_UPLOAD_OK": "false",
        "PHASE281_RESULT_ID": "",
        "PHASE281_CLOUD_INGESTION_API_OK": "false",
        "PHASE281_CLOUD_ADMIN_PAGE_OK": "false",
        "PHASE281_CLOUD_DASHBOARD_OK": "false",
        "LOCAL_SESSION_JSON_VALID": "false",
        "LOCAL_SOURCE_PRESENT": "false",
        "LOCAL_CAPTURE_PRESENT": "false",
        "LOCAL_VIDEO_PRESENT": "false",
        "LOCAL_UPLOAD_PRESENT": "false",
    }

    try:
        handoff = _read_handoff(args.handoff_file)
        _validate_handoff(handoff)
        markers["PHASE281_HANDOFF_LOADED"] = "true"

        remote_session_dir = _resolve_remote_session_dir(
            pi_sshfs_root=args.pi_sshfs_root,
            relative_delivery_dir=str(handoff["relative_delivery_dir"]),
        )
        if remote_session_dir.is_dir():
            markers["PHASE281_REMOTE_SESSION_FOUND"] = "true"
        else:
            raise FileNotFoundError(f"Remote session directory not found: {remote_session_dir}")

        local_session_dir = _resolve_local_session_dir(
            local_delivery_root=args.local_delivery_root,
            handoff=handoff,
            remote_session_dir=remote_session_dir,
        )
        _copy_session(remote_session_dir, local_session_dir)
        markers["PHASE281_SESSION_COPIED"] = "true"

        from classroom_feedback_pipeline import analyze_delivery_package

        analyze_result = analyze_delivery_package(
            local_session_dir,
            config_path=args.config_path,
            output_dir=args.output_dir,
            pending_upload_dir=args.pending_upload_dir,
            upload_mode="directory",
        )
        markers["PHASE281_ANALYSIS_OK"] = "true"
        result_json = Path(str(analyze_result["output_path"]))
        markers["PHASE281_RESULT_JSON"] = str(result_json)

        local_validation = _validate_result_json(result_json)
        for key, value in local_validation.items():
            markers[key] = "true" if value else "false"
        markers["PHASE281_RESULT_JSON_VALID"] = markers["LOCAL_SESSION_JSON_VALID"]

        payload = json.loads(result_json.read_text(encoding="utf-8-sig"))
        result_id = _extract_result_id_from_payload(payload)
        markers["PHASE281_RESULT_ID"] = result_id
        markers["PHASE281_LOCAL_OK"] = "true" if _local_markers_ok(markers) else "false"
        upload_response = _upload_result(args.api_base_url, payload, timeout=args.timeout, session=http_session)
        markers["PHASE281_UPLOAD_OK"] = "true"
        result_id = _extract_result_id_from_response(upload_response) or result_id
        markers["PHASE281_RESULT_ID"] = result_id

        cloud_checks = _validate_cloud_visibility(
            args.api_base_url,
            result_id,
            timeout=args.timeout,
            session=http_session,
        )
        markers.update(cloud_checks)
    except Exception as exc:
        markers["PHASE281_ERROR"] = str(exc)
    finally:
        _print_markers(markers)

    return 0 if markers.get("PHASE281_LOCAL_OK") == "true" and markers.get("PHASE281_UPLOAD_OK") == "true" else 1


def _read_handoff(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Handoff JSON must be an object: {path}")
    return payload


def _validate_handoff(handoff: dict[str, Any]) -> None:
    required_fields = ("success", "relative_delivery_dir", "classroom_id", "session_id")
    missing = [field for field in required_fields if handoff.get(field) in (None, "")]
    if missing:
        raise ValueError(f"Handoff missing required fields: {', '.join(missing)}")
    if handoff.get("success") is not True:
        raise ValueError("Handoff success must be true.")


def _resolve_remote_session_dir(*, pi_sshfs_root: Path, relative_delivery_dir: str) -> Path:
    relative_path = Path(relative_delivery_dir)
    if relative_path.is_absolute():
        return relative_path.resolve()
    return (pi_sshfs_root / relative_path).resolve()


def _resolve_local_session_dir(
    *,
    local_delivery_root: Path,
    handoff: dict[str, Any],
    remote_session_dir: Path,
) -> Path:
    classroom_id = str(handoff["classroom_id"])
    session_id = str(handoff["session_id"])
    date = str(handoff.get("date") or handoff.get("session_date") or "").strip()
    if not date:
        date = _date_from_capture_metadata(remote_session_dir) or _date_from_handoff(handoff) or _today_local_date()
    return (local_delivery_root / classroom_id / date / session_id).resolve()


def _date_from_capture_metadata(remote_session_dir: Path) -> str | None:
    capture_metadata_path = remote_session_dir / "capture_metadata.json"
    if not capture_metadata_path.exists():
        return None
    try:
        payload = json.loads(capture_metadata_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    capture = payload.get("capture") if isinstance(payload, dict) else None
    if not isinstance(capture, dict):
        return None
    captured_at = str(capture.get("captured_at") or "")
    return _date_from_iso_prefix(captured_at)


def _date_from_handoff(handoff: dict[str, Any]) -> str | None:
    for key in ("captured_at", "started_at", "created_at"):
        value = handoff.get(key)
        if value:
            parsed = _date_from_iso_prefix(str(value))
            if parsed:
                return parsed
    return None


def _date_from_iso_prefix(value: str) -> str | None:
    if len(value) >= 10 and value[4:5] == "-" and value[7:8] == "-":
        return value[:10]
    return None


def _today_local_date() -> str:
    return datetime.now().date().isoformat()


def _copy_session(source_dir: Path, target_dir: Path) -> None:
    source_resolved = source_dir.resolve()
    target_resolved = target_dir.resolve()
    if source_resolved == target_resolved:
        raise ValueError(f"Refusing to copy session onto itself: {source_resolved}")
    target_resolved.mkdir(parents=True, exist_ok=True)

    for source_path in source_resolved.rglob("*"):
        relative_path = source_path.relative_to(source_resolved)
        target_path = target_resolved / relative_path
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _validate_result_json(result_json: Path) -> dict[str, bool]:
    try:
        payload = json.loads(result_json.read_text(encoding="utf-8-sig"))
        valid_json = isinstance(payload, dict)
    except Exception:
        payload = {}
        valid_json = False

    teacher = payload.get("teacher") if isinstance(payload.get("teacher"), dict) else {}
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    capture = payload.get("capture") if isinstance(payload.get("capture"), dict) else {}
    video = payload.get("video") if isinstance(payload.get("video"), dict) else {}
    upload = payload.get("upload") if isinstance(payload.get("upload"), dict) else {}

    return {
        "LOCAL_SESSION_JSON_VALID": valid_json,
        "LOCAL_SOURCE_PRESENT": all(source.get(key) for key in ("source_kind", "source_host", "source_path")),
        "LOCAL_CAPTURE_PRESENT": all(capture.get(key) for key in ("device_id", "classroom_id", "captured_at")),
        "LOCAL_VIDEO_PRESENT": bool(video),
        "LOCAL_UPLOAD_PRESENT": all(upload.get(key) for key in ("uploaded_at", "api")),
        "LOCAL_TEACHER_QUESTION_EVENTS_PRESERVED": bool(teacher.get("question_events")),
    }


def _build_http_session() -> requests.Session:
    session = requests.Session()
    # This workflow targets a direct cloud IP and should not inherit broken
    # proxy settings such as HTTP_PROXY/ALL_PROXY=127.0.0.1:9 from the shell.
    session.trust_env = False
    return session


def _upload_result(
    api_base_url: str,
    payload: dict[str, Any],
    *,
    timeout: int,
    session: requests.Session,
) -> requests.Response:
    target_url = f"{api_base_url.rstrip('/')}{UPLOAD_API_PATH}"
    response = session.post(target_url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response


def _extract_result_id_from_payload(payload: dict[str, Any]) -> str:
    return str(payload.get("analysis_id") or payload.get("result_id") or "")


def _extract_result_id_from_response(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    for key in ("result_id", "analysis_id"):
        if payload.get(key):
            return str(payload[key])
    body = payload.get("body")
    if isinstance(body, dict):
        for key in ("result_id", "analysis_id"):
            if body.get(key):
                return str(body[key])
    return ""


def _validate_cloud_visibility(
    api_base_url: str,
    result_id: str,
    *,
    timeout: int,
    session: requests.Session,
) -> dict[str, str]:
    base_url = api_base_url.rstrip("/")
    ingestion_ok = _http_get_visible(
        f"{base_url}/api/admin/ingestion",
        result_id=result_id,
        timeout=timeout,
        session=session,
    )
    admin_page_ok = _http_get_ok(f"{base_url}/admin/ingestion", timeout=timeout, session=session)
    dashboard_url = f"{base_url}/dashboard"
    if result_id:
        dashboard_url = f"{dashboard_url}?{urlencode({'result_id': result_id})}"
    dashboard_ok = _http_get_ok(dashboard_url, timeout=timeout, session=session)
    return {
        "PHASE281_CLOUD_INGESTION_API_OK": "true" if ingestion_ok else "false",
        "PHASE281_CLOUD_ADMIN_PAGE_OK": "true" if admin_page_ok else "false",
        "PHASE281_CLOUD_DASHBOARD_OK": "true" if dashboard_ok else "false",
    }


def _http_get_ok(url: str, *, timeout: int, session: requests.Session) -> bool:
    try:
        response = session.get(url, timeout=timeout)
        return 200 <= response.status_code < 400
    except requests.RequestException:
        return False


def _http_get_visible(url: str, *, result_id: str, timeout: int, session: requests.Session) -> bool:
    try:
        response = session.get(url, timeout=timeout)
    except requests.RequestException:
        return False
    if not (200 <= response.status_code < 400):
        return False
    if not result_id:
        return True
    return result_id in response.text


def _local_markers_ok(markers: dict[str, str]) -> bool:
    required = (
        "PHASE281_HANDOFF_LOADED",
        "PHASE281_REMOTE_SESSION_FOUND",
        "PHASE281_SESSION_COPIED",
        "PHASE281_ANALYSIS_OK",
        "PHASE281_RESULT_JSON_VALID",
        "LOCAL_SESSION_JSON_VALID",
        "LOCAL_SOURCE_PRESENT",
        "LOCAL_VIDEO_PRESENT",
        "LOCAL_UPLOAD_PRESENT",
    )
    return all(markers.get(key) == "true" for key in required)


def _print_markers(markers: dict[str, str]) -> None:
    ordered_keys = [
        "PHASE281_LOCAL_OK",
        "PHASE281_HANDOFF_LOADED",
        "PHASE281_REMOTE_SESSION_FOUND",
        "PHASE281_SESSION_COPIED",
        "PHASE281_ANALYSIS_OK",
        "PHASE281_RESULT_JSON",
        "PHASE281_RESULT_JSON_VALID",
        "PHASE281_UPLOAD_OK",
        "PHASE281_RESULT_ID",
        "PHASE281_CLOUD_INGESTION_API_OK",
        "PHASE281_CLOUD_ADMIN_PAGE_OK",
        "PHASE281_CLOUD_DASHBOARD_OK",
        "LOCAL_SESSION_JSON_VALID",
        "LOCAL_SOURCE_PRESENT",
        "LOCAL_CAPTURE_PRESENT",
        "LOCAL_VIDEO_PRESENT",
        "LOCAL_UPLOAD_PRESENT",
        "PHASE281_ERROR",
    ]
    for key in ordered_keys:
        if key in markers:
            print(f"{key}={markers[key]}")


if __name__ == "__main__":
    raise SystemExit(main())
