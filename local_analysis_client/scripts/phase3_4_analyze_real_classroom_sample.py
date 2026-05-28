from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from classroom_feedback_pipeline import analyze_delivery_package


DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
SOURCE_NAME = "local_real_classroom_sample"
SOURCE_TYPE = "own_real_classroom_session"
DATA_MODE = "local_real_classroom_session"

STATUS_FIELDS = (
    "sample_id",
    "analysis_package_dir",
    "source_video_path",
    "result_json",
    "analysis_status",
    "error",
    "duration_seconds",
    "feedback_score",
    "hand_raise_event_count",
    "active_window_count",
    "source_name",
    "source_type",
    "data_mode",
    "is_demo",
    "is_own_capture",
    "raspberry_pi_capture",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze the Phase 3.4e real full-classroom sample locally.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    parser.add_argument("--manifest-csv", type=Path, default=None)
    parser.add_argument("--analysis-results-dir", type=Path, default=None)
    parser.add_argument("--status-csv", type=Path, default=None)
    parser.add_argument("--pending-upload-dir", type=Path, default=None)
    parser.add_argument("--config-path", type=Path, default=None)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    reports_dir = sample_root / "reports"
    manifest_csv = args.manifest_csv.resolve() if args.manifest_csv else reports_dir / "real_classroom_sample_manifest.csv"
    analysis_results_dir = args.analysis_results_dir.resolve() if args.analysis_results_dir else sample_root / "analysis_results"
    status_csv = args.status_csv.resolve() if args.status_csv else reports_dir / "real_classroom_analysis_status.csv"
    pending_upload_dir = args.pending_upload_dir.resolve() if args.pending_upload_dir else reports_dir / "real_classroom_pending_upload"

    for path in (reports_dir, analysis_results_dir, pending_upload_dir):
        path.mkdir(parents=True, exist_ok=True)

    manifest_rows = _read_rows(manifest_csv) if manifest_csv.exists() else []
    status_rows = [
        _analyze_one(
            row=row,
            analysis_results_dir=analysis_results_dir,
            pending_upload_dir=pending_upload_dir,
            config_path=args.config_path,
        )
        for row in manifest_rows
        if row.get("ready_for_analysis") == "true"
    ]
    _write_rows(status_csv, status_rows)

    success_count = sum(1 for row in status_rows if row.get("analysis_status") == "success")
    failed_count = sum(1 for row in status_rows if row.get("analysis_status") == "failed")
    ok = success_count >= 1
    print(f"PHASE34_REAL_CLASSROOM_ANALYSIS_PLAN_COUNT={len(status_rows)}")
    print(f"PHASE34_REAL_CLASSROOM_ANALYSIS_SUCCESS_COUNT={success_count}")
    print(f"PHASE34_REAL_CLASSROOM_ANALYSIS_FAILED_COUNT={failed_count}")
    print(f"PHASE34_REAL_CLASSROOM_ANALYSIS_RESULTS_DIR={analysis_results_dir}")
    print(f"PHASE34_REAL_CLASSROOM_ANALYSIS_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _analyze_one(
    *,
    row: dict[str, str],
    analysis_results_dir: Path,
    pending_upload_dir: Path,
    config_path: Path | None,
) -> dict[str, str]:
    sample_id = str(row.get("sample_id") or "phase34e_real_classroom")
    result_json = analysis_results_dir / f"{sample_id}.json"
    try:
        package_dir = Path(str(row.get("analysis_package_dir") or "")).resolve()
        if not package_dir.exists():
            raise FileNotFoundError(f"analysis_package_dir_missing: {package_dir}")
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
        _attach_real_classroom_metadata(payload, row)
        result_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        stats = _extract_stats(payload)
        return _status_row(row, result_json=result_json, status="success", error="", stats=stats)
    except Exception as exc:
        return _status_row(row, result_json=result_json, status="failed", error=f"{type(exc).__name__}: {exc}", stats={})


def _attach_real_classroom_metadata(payload: dict[str, Any], row: dict[str, str]) -> None:
    payload["source_name"] = SOURCE_NAME
    payload["source_type"] = SOURCE_TYPE
    payload["data_mode"] = DATA_MODE
    payload["is_demo"] = False
    payload["is_own_capture"] = True
    source = payload.setdefault("source", {})
    if isinstance(source, dict):
        source.update(
            {
                "source_name": SOURCE_NAME,
                "source_type": SOURCE_TYPE,
                "data_mode": DATA_MODE,
                "is_demo": False,
                "is_own_capture": True,
            }
        )
    payload["phase34_real_classroom"] = {
        "sample_id": str(row.get("sample_id") or ""),
        "source_video_path": str(row.get("source_video_path") or ""),
        "raspberry_pi_capture": str(row.get("raspberry_pi_capture") or "unknown"),
        "raspberry_pi_capture_note": str(row.get("raspberry_pi_capture_note") or ""),
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
        "data_mode": DATA_MODE,
        "is_demo": False,
        "is_own_capture": True,
    }


def _extract_stats(payload: dict[str, Any]) -> dict[str, str]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    students = payload.get("students") if isinstance(payload.get("students"), dict) else {}
    timeline = payload.get("timeline") if isinstance(payload.get("timeline"), dict) else {}
    activity_curve = timeline.get("activity_curve") if isinstance(timeline.get("activity_curve"), list) else []
    return {
        "duration_seconds": str(_safe_int(payload.get("time", {}).get("duration_seconds") if isinstance(payload.get("time"), dict) else "")),
        "feedback_score": _format_float(summary.get("feedback_score")),
        "hand_raise_event_count": str(_safe_int(students.get("hand_raise_event_count"))),
        "active_window_count": str(sum(1 for value in activity_curve if _safe_float(value) > 0)),
    }


def _status_row(
    row: dict[str, str],
    *,
    result_json: Path,
    status: str,
    error: str,
    stats: dict[str, str],
) -> dict[str, str]:
    return {
        "sample_id": str(row.get("sample_id") or ""),
        "analysis_package_dir": str(row.get("analysis_package_dir") or ""),
        "source_video_path": str(row.get("source_video_path") or ""),
        "result_json": str(result_json),
        "analysis_status": status,
        "error": error,
        "duration_seconds": stats.get("duration_seconds", str(row.get("duration_seconds") or "")),
        "feedback_score": stats.get("feedback_score", ""),
        "hand_raise_event_count": stats.get("hand_raise_event_count", ""),
        "active_window_count": stats.get("active_window_count", ""),
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
        "data_mode": DATA_MODE,
        "is_demo": "false",
        "is_own_capture": "true",
        "raspberry_pi_capture": str(row.get("raspberry_pi_capture") or "unknown"),
    }


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=STATUS_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in STATUS_FIELDS})


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
