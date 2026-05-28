from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from classroom_feedback_pipeline import analyze_delivery_package


DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
SAMPLE_ID = "local_imported_sav_full_classroom_20200908_17"
SOURCE_VIDEO_ID = "20200908_17"
SOURCE_DATASET = "SAV"
SOURCE_TYPE = "local_imported_video"
SAMPLE_TYPE = "external_full_classroom_video"
DATA_MODE = "external_full_classroom_video"

STATUS_FIELDS = (
    "sample_id",
    "source_video_id",
    "video_path",
    "analysis_package_dir",
    "result_json",
    "analysis_status",
    "error",
    "duration_seconds",
    "feedback_score",
    "attention_score",
    "response_score",
    "teacher_question_count",
    "hand_raise_event_count",
    "active_window_count",
    "source_dataset",
    "source_type",
    "sample_type",
    "is_pi_capture",
    "is_own_capture",
    "is_local_processed",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze the local imported SAV full-classroom video.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    parser.add_argument("--config-path", type=Path, default=None)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    reports_dir = sample_root / "reports"
    analysis_results_dir = sample_root / "analysis_results"
    pending_upload_dir = reports_dir / "local_imported_full_classroom_pending_upload"
    manifest_csv = reports_dir / "local_imported_full_classroom_manifest.csv"
    status_csv = reports_dir / "local_imported_full_classroom_analysis_status.csv"
    for path in (reports_dir, analysis_results_dir, pending_upload_dir):
        path.mkdir(parents=True, exist_ok=True)

    manifest = _read_first_row(manifest_csv)
    status_row = _analyze_one(
        manifest=manifest,
        sample_root=sample_root,
        analysis_results_dir=analysis_results_dir,
        pending_upload_dir=pending_upload_dir,
        config_path=args.config_path,
    )
    _write_rows(status_csv, [status_row])
    success = status_row.get("analysis_status") == "success"
    print("PHASE34E_LOCAL_IMPORTED_ANALYSIS_PLAN_COUNT=1")
    print(f"PHASE34E_LOCAL_IMPORTED_ANALYSIS_SUCCESS={_bool_text(success)}")
    print(f"PHASE34E_LOCAL_IMPORTED_ANALYSIS_STATUS={status_row.get('analysis_status', '')}")
    print(f"PHASE34E_LOCAL_IMPORTED_ANALYSIS_RESULTS_DIR={analysis_results_dir}")
    print(f"PHASE34E_LOCAL_IMPORTED_RESULT_JSON={status_row.get('result_json', '')}")
    if status_row.get("error"):
        print(f"PHASE34E_LOCAL_IMPORTED_ANALYSIS_ERROR={status_row['error']}")
    return 0 if success else 1


def _analyze_one(
    *,
    manifest: dict[str, str],
    sample_root: Path,
    analysis_results_dir: Path,
    pending_upload_dir: Path,
    config_path: Path | None,
) -> dict[str, str]:
    result_json = analysis_results_dir / f"{SAMPLE_ID}.json"
    try:
        if not manifest:
            raise FileNotFoundError("manifest_missing")
        video_path = Path(str(manifest.get("video_path") or "")).resolve()
        if not video_path.exists():
            raise FileNotFoundError(f"video_missing: {video_path}")
        package_dir = _build_analysis_package(sample_root=sample_root, manifest=manifest, video_path=video_path)
        result = analyze_delivery_package(
            package_dir,
            config_path=config_path,
            output_dir=analysis_results_dir,
            pending_upload_dir=pending_upload_dir,
            upload_mode="directory",
        )
        generated_path = Path(str(result.get("output_path") or result_json)).resolve()
        if generated_path.exists() and generated_path != result_json:
            shutil.copy2(generated_path, result_json)
        payload = json.loads(result_json.read_text(encoding="utf-8-sig"))
        _attach_local_imported_metadata(payload, manifest)
        result_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        stats = _extract_stats(payload)
        return _status_row(manifest, result_json=result_json, status="success", error="", stats=stats)
    except Exception as exc:
        return _status_row(manifest, result_json=result_json, status="failed", error=f"{type(exc).__name__}: {exc}", stats={})


def _build_analysis_package(*, sample_root: Path, manifest: dict[str, str], video_path: Path) -> Path:
    package_dir = sample_root / "packages" / SAMPLE_ID
    package_dir.mkdir(parents=True, exist_ok=True)
    package_video = package_dir / "video.mp4"
    if not package_video.exists() or package_video.stat().st_size != video_path.stat().st_size:
        _link_or_copy(video_path, package_video)
    duration_seconds = _probe_duration_seconds(video_path)
    metadata = {
        "analysis_id": SAMPLE_ID,
        "classroom_id": "SAV_local_imported",
        "session_id": SAMPLE_ID,
        "video_id": f"video_{SOURCE_VIDEO_ID}",
        "recorded_at": "2020-09-08T00:00:00Z",
        "duration_seconds": duration_seconds,
        "window_size_seconds": 20,
        "source_kind": "local_imported_video",
        "source_path": str(video_path),
        "source_dataset": SOURCE_DATASET,
        "source_type": SOURCE_TYPE,
        "sample_type": SAMPLE_TYPE,
        "data_mode": DATA_MODE,
        "is_pi_capture": False,
        "is_own_capture": False,
        "is_local_processed": True,
        "expected_key_event_note": manifest.get("expected_key_event_note", ""),
    }
    capture_metadata = {
        "capture": {
            "device_id": "local_imported_sav",
            "classroom_id": "SAV_local_imported",
            "captured_at": "2020-09-08T00:00:00Z",
            "video_path": str(video_path),
            "source_dataset": SOURCE_DATASET,
            "source_type": SOURCE_TYPE,
            "sample_type": SAMPLE_TYPE,
            "data_mode": DATA_MODE,
            "is_pi_capture": False,
            "is_own_capture": False,
            "is_local_processed": True,
        },
        "video": {
            "raw_video_path": str(video_path),
            "duration_seconds": duration_seconds,
            "format": "mp4",
            "browser_compatible": True,
        },
    }
    _write_json(package_dir / "metadata.json", metadata)
    _write_json(package_dir / "capture_metadata.json", capture_metadata)
    _write_json(package_dir / "teacher_transcript.json", [])
    _write_json(
        package_dir / "teacher_questions.json",
        {
            "status": "unavailable",
            "questions": [],
            "summary": {"question_count": 0},
            "reason": "local_imported_sav_full_video_no_teacher_transcript",
        },
    )
    return package_dir


def _attach_local_imported_metadata(payload: dict[str, Any], manifest: dict[str, str]) -> None:
    payload["source_dataset"] = SOURCE_DATASET
    payload["source_type"] = SOURCE_TYPE
    payload["sample_type"] = SAMPLE_TYPE
    payload["data_mode"] = DATA_MODE
    payload["is_pi_capture"] = False
    payload["is_own_capture"] = False
    payload["is_local_processed"] = True
    source = payload.setdefault("source", {})
    if isinstance(source, dict):
        source.update(
            {
                "source_dataset": SOURCE_DATASET,
                "source_type": SOURCE_TYPE,
                "sample_type": SAMPLE_TYPE,
                "data_mode": DATA_MODE,
                "is_pi_capture": False,
                "is_own_capture": False,
                "is_local_processed": True,
            }
        )
    payload["phase34e_local_imported_full_classroom"] = {
        "sample_id": SAMPLE_ID,
        "source_video_id": SOURCE_VIDEO_ID,
        "video_path": manifest.get("video_path", ""),
        "source_dataset": SOURCE_DATASET,
        "source_type": SOURCE_TYPE,
        "sample_type": SAMPLE_TYPE,
        "is_pi_capture": False,
        "is_own_capture": False,
        "is_local_processed": True,
        "expected_key_event_note": manifest.get("expected_key_event_note", ""),
    }


def _extract_stats(payload: dict[str, Any]) -> dict[str, str]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    students = payload.get("students") if isinstance(payload.get("students"), dict) else {}
    timeline = payload.get("timeline") if isinstance(payload.get("timeline"), dict) else {}
    activity_curve = timeline.get("activity_curve") if isinstance(timeline.get("activity_curve"), list) else []
    duration = payload.get("time", {}).get("duration_seconds") if isinstance(payload.get("time"), dict) else ""
    return {
        "duration_seconds": str(_safe_int(duration)),
        "feedback_score": _format_float(summary.get("feedback_score")),
        "attention_score": _format_float(summary.get("attention_score")),
        "response_score": _format_float(summary.get("response_score")),
        "teacher_question_count": str(_safe_int(summary.get("teacher_question_count"))),
        "hand_raise_event_count": str(_safe_int(students.get("hand_raise_event_count"))),
        "active_window_count": str(sum(1 for value in activity_curve if _safe_float(value) > 0)),
    }


def _status_row(
    manifest: dict[str, str],
    *,
    result_json: Path,
    status: str,
    error: str,
    stats: dict[str, str],
) -> dict[str, str]:
    return {
        "sample_id": SAMPLE_ID,
        "source_video_id": SOURCE_VIDEO_ID,
        "video_path": manifest.get("video_path", ""),
        "analysis_package_dir": manifest.get("analysis_package_dir", str(DEFAULT_SAMPLE_ROOT / "packages" / SAMPLE_ID)),
        "result_json": str(result_json),
        "analysis_status": status,
        "error": error,
        "duration_seconds": stats.get("duration_seconds", manifest.get("duration_seconds", "")),
        "feedback_score": stats.get("feedback_score", ""),
        "attention_score": stats.get("attention_score", ""),
        "response_score": stats.get("response_score", ""),
        "teacher_question_count": stats.get("teacher_question_count", ""),
        "hand_raise_event_count": stats.get("hand_raise_event_count", ""),
        "active_window_count": stats.get("active_window_count", ""),
        "source_dataset": SOURCE_DATASET,
        "source_type": SOURCE_TYPE,
        "sample_type": SAMPLE_TYPE,
        "is_pi_capture": "false",
        "is_own_capture": "false",
        "is_local_processed": "true",
    }


def _link_or_copy(source: Path, target: Path) -> None:
    if target.exists():
        target.unlink()
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def _probe_duration_seconds(video_path: Path) -> int:
    try:
        import cv2

        capture = cv2.VideoCapture(str(video_path))
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
            if fps > 0 and frame_count > 0:
                return max(1, int(frame_count / fps))
        finally:
            capture.release()
    except Exception:
        return 0
    return 0


def _read_first_row(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    return rows[0] if rows else {}


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=STATUS_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in STATUS_FIELDS})


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(str(value or "0"))
    except ValueError:
        return 0.0


def _format_float(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
