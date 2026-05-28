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


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
SOURCE_NAME = "SAV"
SOURCE_TYPE = "public_dataset"
DATA_MODE = "external_real_clip"

STATUS_FIELDS = (
    "dataset_order",
    "clip_id",
    "package_dir",
    "result_json",
    "analysis_status",
    "error",
    "final_phase34_category",
    "final_phase34_category_cn",
    "source_name",
    "source_type",
    "data_mode",
    "is_demo",
    "is_own_capture",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local analysis for the Phase 3.4 SAV-50 clip packages.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--manifest-csv", type=Path, default=None)
    parser.add_argument("--analysis-results-dir", type=Path, default=None)
    parser.add_argument("--pending-upload-dir", type=Path, default=None)
    parser.add_argument("--status-csv", type=Path, default=None)
    parser.add_argument("--config-path", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--clip-id", action="append", default=[])
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    manifest_csv = args.manifest_csv.resolve() if args.manifest_csv else reports_dir / "sav50_clip_packages_manifest.csv"
    analysis_results_dir = args.analysis_results_dir.resolve() if args.analysis_results_dir else sav_root / "analysis_results"
    pending_upload_dir = args.pending_upload_dir.resolve() if args.pending_upload_dir else reports_dir / "sav50_pending_upload"
    status_csv = args.status_csv.resolve() if args.status_csv else reports_dir / "sav50_local_analysis_status.csv"

    manifest_rows = _select_rows(_read_rows(manifest_csv) if manifest_csv.exists() else [], clip_ids=args.clip_id, limit=args.limit)
    analysis_results_dir.mkdir(parents=True, exist_ok=True)
    pending_upload_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    status_rows: list[dict[str, str]] = []
    for manifest_row in manifest_rows:
        status_rows.append(
            _analyze_one(
                manifest_row=manifest_row,
                analysis_results_dir=analysis_results_dir,
                pending_upload_dir=pending_upload_dir,
                config_path=args.config_path,
            )
        )
        _write_rows(status_csv, status_rows)

    _write_rows(status_csv, status_rows)
    success_count = sum(1 for row in status_rows if row.get("analysis_status") == "success")
    failed_count = sum(1 for row in status_rows if row.get("analysis_status") == "failed")
    ok = success_count >= 1

    print(f"PHASE34_SAV50_ANALYSIS_PLAN_COUNT={len(status_rows)}")
    print(f"PHASE34_SAV50_ANALYSIS_SUCCESS_COUNT={success_count}")
    print(f"PHASE34_SAV50_ANALYSIS_FAILED_COUNT={failed_count}")
    print(f"PHASE34_SAV50_ANALYSIS_RESULTS_DIR={analysis_results_dir}")
    print(f"PHASE34_SAV50_LOCAL_ANALYSIS_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _analyze_one(
    *,
    manifest_row: dict[str, str],
    analysis_results_dir: Path,
    pending_upload_dir: Path,
    config_path: Path | None,
) -> dict[str, str]:
    clip_id = str(manifest_row.get("clip_id") or "")
    result_json = analysis_results_dir / f"{clip_id}.json"
    try:
        package_dir = Path(str(manifest_row.get("package_dir") or "")).resolve()
        if not package_dir.exists():
            raise FileNotFoundError(f"package_dir_missing: {package_dir}")
        analyze_result = analyze_delivery_package(
            package_dir,
            config_path=config_path,
            output_dir=analysis_results_dir,
            pending_upload_dir=pending_upload_dir,
            upload_mode="directory",
        )
        generated_path = Path(str(analyze_result.get("output_path") or result_json)).resolve()
        if generated_path != result_json and generated_path.exists():
            shutil.copy2(generated_path, result_json)
        if not result_json.exists():
            raise FileNotFoundError(f"analysis_result_missing: {result_json}")
        payload = json.loads(result_json.read_text(encoding="utf-8-sig"))
        _attach_sav_metadata(payload, manifest_row)
        result_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return _status_row(manifest_row, result_json=result_json, status="success", error="")
    except Exception as exc:
        return _status_row(manifest_row, result_json=result_json, status="failed", error=f"{type(exc).__name__}: {exc}")


def _attach_sav_metadata(payload: dict[str, Any], manifest_row: dict[str, str]) -> None:
    payload["data_mode"] = DATA_MODE
    payload["source_name"] = SOURCE_NAME
    payload["source_type"] = SOURCE_TYPE
    payload["is_demo"] = False
    payload["is_own_capture"] = False
    source = payload.setdefault("source", {})
    if isinstance(source, dict):
        source["source_name"] = SOURCE_NAME
        source["source_type"] = SOURCE_TYPE
        source["data_mode"] = DATA_MODE
        source["is_demo"] = False
        source["is_own_capture"] = False
    payload["phase34_sav"] = {
        "clip_id": str(manifest_row.get("clip_id") or ""),
        "final_phase34_category": str(manifest_row.get("final_phase34_category") or ""),
        "final_phase34_category_cn": str(manifest_row.get("final_phase34_category_cn") or ""),
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
        "data_mode": DATA_MODE,
        "is_demo": False,
        "is_own_capture": False,
    }


def _status_row(manifest_row: dict[str, str], *, result_json: Path, status: str, error: str) -> dict[str, str]:
    return {
        "dataset_order": str(manifest_row.get("dataset_order") or ""),
        "clip_id": str(manifest_row.get("clip_id") or ""),
        "package_dir": str(manifest_row.get("package_dir") or ""),
        "result_json": str(result_json),
        "analysis_status": status,
        "error": error,
        "final_phase34_category": str(manifest_row.get("final_phase34_category") or ""),
        "final_phase34_category_cn": str(manifest_row.get("final_phase34_category_cn") or ""),
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
        "data_mode": DATA_MODE,
        "is_demo": "false",
        "is_own_capture": "false",
    }


def _select_rows(rows: list[dict[str, str]], *, clip_ids: list[str], limit: int | None) -> list[dict[str, str]]:
    selected = sorted(rows, key=_dataset_order_key)
    if clip_ids:
        clip_id_set = set(clip_ids)
        selected = [row for row in selected if str(row.get("clip_id") or "") in clip_id_set]
    if limit is not None:
        selected = selected[: max(limit, 0)]
    return selected


def _dataset_order_key(row: dict[str, str]) -> tuple[int, str]:
    try:
        return (int(str(row.get("dataset_order") or "0")), str(row.get("clip_id") or ""))
    except ValueError:
        return (0, str(row.get("clip_id") or ""))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=STATUS_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in STATUS_FIELDS})


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
