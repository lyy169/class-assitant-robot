from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from classroom_feedback_pipeline import analyze_delivery_package


DEFAULT_DELIVERY_ROOT = REPO_ROOT / "captures_local_delivery"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "processed_results" / "session_consume_manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan delivery root and consume ready session packages.")
    parser.add_argument("--delivery-root", type=Path, default=DEFAULT_DELIVERY_ROOT, help="Root directory to scan recursively.")
    parser.add_argument("--config-path", type=Path, default=None, help="Optional config.yaml path.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Optional output directory for generated JSON.")
    parser.add_argument("--pending-upload-dir", type=Path, default=None, help="Optional fallback directory for failed uploads.")
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH, help="Local consume manifest path.")
    parser.add_argument("--upload-mode", choices=["auto", "http", "directory"], default="auto")
    parser.add_argument("--enrich-missing-signals", action="store_true", help="Attempt local transcript/question enrichment before analysis.")
    parser.add_argument("--enrichment-root", type=Path, default=REPO_ROOT / "processed_results" / "delivery_enrichment")
    parser.add_argument("--enrich-engine", default="auto")
    parser.add_argument("--enrich-model", default=str(REPO_ROOT.parent / "asr_models" / "faster-whisper-base"))
    parser.add_argument("--enrich-language", default="auto")
    parser.add_argument("--enrich-device", default="cpu")
    parser.add_argument("--enrich-compute-type", default="int8")
    parser.add_argument("--enrich-force-transcript", action="store_true")
    parser.add_argument("--enrich-force-questions", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Optional max number of ready sessions to consume.")
    args = parser.parse_args()

    result = consume_ready_sessions(
        delivery_root=args.delivery_root,
        config_path=args.config_path,
        output_dir=args.output_dir,
        pending_upload_dir=args.pending_upload_dir,
        manifest_path=args.manifest_path,
        upload_mode=args.upload_mode,
        limit=args.limit,
        enrich_missing_signals=args.enrich_missing_signals,
        enrichment_root=args.enrichment_root,
        enrich_engine=args.enrich_engine,
        enrich_model=args.enrich_model,
        enrich_language=args.enrich_language,
        enrich_device=args.enrich_device,
        enrich_compute_type=args.enrich_compute_type,
        enrich_force_transcript=args.enrich_force_transcript,
        enrich_force_questions=args.enrich_force_questions,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def consume_ready_sessions(
    *,
    delivery_root: str | Path,
    config_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    pending_upload_dir: str | Path | None = None,
    manifest_path: str | Path | None = None,
    upload_mode: str = "auto",
    limit: int = 0,
    enrich_missing_signals: bool = False,
    enrichment_root: str | Path | None = None,
    enrich_engine: str = "auto",
    enrich_model: str = "base",
    enrich_language: str = "auto",
    enrich_device: str = "cpu",
    enrich_compute_type: str = "int8",
    enrich_force_transcript: bool = False,
    enrich_force_questions: bool = False,
) -> dict[str, Any]:
    root = Path(delivery_root).resolve()
    manifest_file = Path(manifest_path).resolve() if manifest_path else DEFAULT_MANIFEST_PATH
    manifest = _load_manifest(manifest_file)

    candidates = sorted(
        (path.parent for path in root.rglob("metadata.json")),
        key=lambda item: (len(item.parts), str(item).lower()),
    )

    results: list[dict[str, Any]] = []
    scanned_count = 0
    ready_count = 0
    consumed_count = 0
    failed_count = 0
    skipped_not_ready_count = 0
    skipped_already_consumed_count = 0

    remaining_limit = limit if limit > 0 else None

    for package_dir in candidates:
        scanned_count += 1
        session_result = _inspect_session_candidate(package_dir)
        metadata = session_result.get("metadata") or {}
        session_key = _build_session_key(package_dir, metadata)
        session_result["session_key"] = session_key

        if not session_result["is_ready"]:
            skipped_not_ready_count += 1
            results.append(session_result)
            continue

        ready_count += 1

        if _is_already_consumed(manifest, session_key):
            skipped_already_consumed_count += 1
            results.append(
                {
                    "package_dir": str(package_dir),
                    "session_key": session_key,
                    "status": "skipped_already_consumed",
                    "analysis_id": metadata.get("analysis_id"),
                }
            )
            continue

        if remaining_limit is not None and remaining_limit <= 0:
            results.append(
                {
                    "package_dir": str(package_dir),
                    "session_key": session_key,
                    "status": "skipped_limit_reached",
                    "analysis_id": metadata.get("analysis_id"),
                }
            )
            continue

        attempt_at = _utc_now_iso()
        try:
            if enrich_missing_signals:
                analyze_result = _run_enrich_and_analyze(
                    package_dir=package_dir,
                    config_path=config_path,
                    output_dir=output_dir,
                    pending_upload_dir=pending_upload_dir,
                    upload_mode=upload_mode,
                    enrichment_root=enrichment_root,
                    enrich_engine=enrich_engine,
                    enrich_model=enrich_model,
                    enrich_language=enrich_language,
                    enrich_device=enrich_device,
                    enrich_compute_type=enrich_compute_type,
                    enrich_force_transcript=enrich_force_transcript,
                    enrich_force_questions=enrich_force_questions,
                )
            else:
                analyze_result = analyze_delivery_package(
                    package_dir,
                    config_path=config_path,
                    output_dir=output_dir,
                    pending_upload_dir=pending_upload_dir,
                    upload_mode=upload_mode,
                )
            delivery = analyze_result.get("delivery", {})
            manifest["sessions"][session_key] = {
                "analysis_id": analyze_result.get("analysis_id"),
                "package_dir": str(package_dir),
                "analysis_status": "success",
                "last_attempt_at": attempt_at,
                "output_path": analyze_result.get("output_path"),
                "upload_mode": delivery.get("mode"),
                "upload_status": delivery.get("status"),
                "http_status": delivery.get("http_status"),
                "delivery_target": delivery.get("target"),
                "transcript_action": analyze_result.get("transcript_action"),
                "question_action": analyze_result.get("question_action"),
                "transcript_segment_count": analyze_result.get("transcript_segment_count"),
                "question_event_count": analyze_result.get("question_event_count"),
            }
            _write_manifest(manifest_file, manifest)

            consumed_count += 1
            results.append(
                {
                    "package_dir": str(package_dir),
                    "session_key": session_key,
                    "status": "consumed",
                    "analysis_id": analyze_result.get("analysis_id"),
                    "output_path": analyze_result.get("output_path"),
                    "upload_status": delivery.get("status"),
                    "http_status": delivery.get("http_status"),
                    "delivery_target": delivery.get("target"),
                    "transcript_action": analyze_result.get("transcript_action"),
                    "question_action": analyze_result.get("question_action"),
                    "transcript_segment_count": analyze_result.get("transcript_segment_count"),
                    "question_event_count": analyze_result.get("question_event_count"),
                }
            )
            if remaining_limit is not None:
                remaining_limit -= 1
        except Exception as exc:
            failed_count += 1
            manifest["sessions"][session_key] = {
                "analysis_id": metadata.get("analysis_id"),
                "package_dir": str(package_dir),
                "analysis_status": "failed",
                "last_attempt_at": attempt_at,
                "error": str(exc),
            }
            _write_manifest(manifest_file, manifest)
            results.append(
                {
                    "package_dir": str(package_dir),
                    "session_key": session_key,
                    "status": "failed",
                    "analysis_id": metadata.get("analysis_id"),
                    "error": str(exc),
                }
            )

    manifest["updated_at"] = _utc_now_iso()
    _write_manifest(manifest_file, manifest)

    return {
        "delivery_root": str(root),
        "manifest_path": str(manifest_file),
        "scanned_count": scanned_count,
        "ready_count": ready_count,
        "consumed_count": consumed_count,
        "failed_count": failed_count,
        "skipped_not_ready_count": skipped_not_ready_count,
        "skipped_already_consumed_count": skipped_already_consumed_count,
        "results": results,
    }


def _run_enrich_and_analyze(
    *,
    package_dir: Path,
    config_path: str | Path | None,
    output_dir: str | Path | None,
    pending_upload_dir: str | Path | None,
    upload_mode: str,
    enrichment_root: str | Path | None,
    enrich_engine: str,
    enrich_model: str,
    enrich_language: str,
    enrich_device: str,
    enrich_compute_type: str,
    enrich_force_transcript: bool,
    enrich_force_questions: bool,
) -> dict[str, Any]:
    script_path = REPO_ROOT / "scripts" / "phase3_5c_enrich_and_analyze_delivery_package.py"
    resolved_enrichment_root = Path(enrichment_root).resolve() if enrichment_root else REPO_ROOT / "processed_results" / "delivery_enrichment"
    command = [
        sys.executable,
        str(script_path),
        str(package_dir),
        "--upload-mode",
        upload_mode,
        "--enrichment-root",
        str(resolved_enrichment_root),
        "--engine",
        enrich_engine,
        "--model",
        enrich_model,
        "--language",
        enrich_language,
        "--device",
        enrich_device,
        "--compute-type",
        enrich_compute_type,
    ]
    if config_path:
        command.extend(["--config-path", str(config_path)])
    if output_dir:
        command.extend(["--output-dir", str(output_dir)])
    if pending_upload_dir:
        command.extend(["--pending-upload-dir", str(pending_upload_dir)])
    if enrich_force_transcript:
        command.append("--force-transcript")
    if enrich_force_questions:
        command.append("--force-questions")

    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"enrich_and_analyze_failed: exit_code={completed.returncode}")

    status_path = resolved_enrichment_root / package_dir.name / "enrich_and_analyze_status.json"
    if not status_path.exists():
        raise FileNotFoundError(f"enrich_status_missing: {status_path}")
    payload = json.loads(status_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"enrich_status_invalid: {status_path}")
    delivery = payload.get("delivery") if isinstance(payload.get("delivery"), dict) else {}
    return {
        "analysis_id": payload.get("analysis_id"),
        "output_path": payload.get("output_path"),
        "delivery": delivery,
        "transcript_action": payload.get("transcript_action"),
        "question_action": payload.get("question_action"),
        "transcript_segment_count": payload.get("transcript_segment_count"),
        "question_event_count": payload.get("question_event_count"),
        "transcript_error": payload.get("transcript_error"),
        "question_error": payload.get("question_error"),
    }


def _inspect_session_candidate(package_dir: Path) -> dict[str, Any]:
    metadata_path = package_dir / "metadata.json"
    try:
        metadata = _read_metadata_json(metadata_path)
    except Exception as exc:
        return {
            "package_dir": str(package_dir),
            "status": "skipped_not_ready",
            "reason": f"metadata_unreadable: {exc}",
            "is_ready": False,
            "metadata": None,
        }
    metadata = _normalize_metadata(package_dir, metadata)

    session_ready = metadata.get("session_ready") is True
    delivery_status = str(metadata.get("delivery_status") or "").strip().lower()
    required_metadata_fields = ("classroom_id", "session_id")
    missing_metadata_fields = [field for field in required_metadata_fields if not metadata.get(field)]
    file_integrity = metadata.get("file_integrity") if isinstance(metadata.get("file_integrity"), dict) else {}

    video_exists = (package_dir / "video.mp4").exists()
    metadata_exists = metadata_path.exists()
    required_integrity_failures: list[str] = []
    if file_integrity.get("metadata_json") is False:
        required_integrity_failures.append("metadata_json=false")
    if file_integrity.get("video_mp4") is False:
        required_integrity_failures.append("video_mp4=false")

    reasons: list[str] = []
    if not session_ready:
        reasons.append("session_ready!=true")
    if delivery_status != "ready":
        reasons.append(f"delivery_status={delivery_status or '<missing>'}")
    if missing_metadata_fields:
        reasons.append(f"missing_metadata_fields={','.join(missing_metadata_fields)}")
    if not metadata_exists:
        reasons.append("metadata.json_missing")
    if not video_exists:
        reasons.append("video.mp4_missing")
    reasons.extend(required_integrity_failures)

    if reasons:
        return {
            "package_dir": str(package_dir),
            "status": "skipped_not_ready",
            "reason": "; ".join(reasons),
            "is_ready": False,
            "metadata": metadata,
        }

    return {
        "package_dir": str(package_dir),
        "status": "ready",
        "reason": None,
        "is_ready": True,
        "metadata": metadata,
    }


def _build_session_key(package_dir: Path, metadata: dict[str, Any]) -> str:
    analysis_id = metadata.get("analysis_id")
    if analysis_id:
        return str(analysis_id)
    return str(package_dir.resolve()).lower()


def _read_metadata_json(metadata_path: Path) -> dict[str, Any]:
    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            payload = json.loads(metadata_path.read_text(encoding=encoding))
        except Exception as exc:
            last_error = exc
            continue
        if isinstance(payload, dict):
            return payload
        raise ValueError(f"metadata_root_not_object: {metadata_path}")
    if last_error is not None:
        raise last_error
    raise ValueError(f"metadata_unreadable: {metadata_path}")


def _normalize_metadata(package_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(metadata)
    if not normalized.get("session_id"):
        normalized["session_id"] = (
            normalized.get("capture_id")
            or normalized.get("session_uuid")
            or package_dir.name
        )
    return normalized


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("sessions"), dict):
                payload.setdefault("schema_version", "v1")
                payload.setdefault("updated_at", _utc_now_iso())
                return payload
        except Exception:
            pass
    return {
        "schema_version": "v1",
        "updated_at": _utc_now_iso(),
        "sessions": {},
    }


def _write_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = _utc_now_iso()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_already_consumed(manifest: dict[str, Any], session_key: str) -> bool:
    session_record = manifest.get("sessions", {}).get(session_key, {})
    return session_record.get("analysis_status") == "success"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
