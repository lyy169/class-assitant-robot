from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
SOURCE_NAME = "SAV"
SOURCE_TYPE = "public_dataset"
DATA_MODE = "external_real_clip"
PHASE = "3.4"

MANIFEST_FIELDS = (
    "dataset_order",
    "clip_id",
    "source_video_id",
    "package_dir",
    "video_path",
    "standardized_video_path",
    "metadata_path",
    "capture_metadata_path",
    "teacher_transcript_path",
    "teacher_questions_path",
    "sav_source_annotation_path",
    "human_review_path",
    "manual_clip_path",
    "package_created",
    "video_present",
    "standardized_video_present",
    "metadata_valid",
    "final_phase34_category",
    "final_phase34_category_cn",
    "source_name",
    "source_type",
    "data_mode",
    "is_demo",
    "is_own_capture",
    "notes",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local delivery packages for the Phase 3.4 SAV-50 clips.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--review-csv", type=Path, default=None)
    parser.add_argument("--manual-clips-dir", type=Path, default=None)
    parser.add_argument("--clip-packages-dir", type=Path, default=None)
    parser.add_argument("--manifest-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    review_csv = args.review_csv.resolve() if args.review_csv else reports_dir / "final_sav50_manual_review_results.csv"
    manual_clips_dir = args.manual_clips_dir.resolve() if args.manual_clips_dir else sav_root / "manual_clips"
    clip_packages_dir = args.clip_packages_dir.resolve() if args.clip_packages_dir else sav_root / "clip_packages"
    manifest_csv = args.manifest_csv.resolve() if args.manifest_csv else reports_dir / "sav50_clip_packages_manifest.csv"

    rows = _read_rows(review_csv) if review_csv.exists() else []
    manifest_rows: list[dict[str, str]] = []
    clip_packages_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    for row in sorted(rows, key=_dataset_order_key):
        manifest_rows.append(
            _build_package(
                review_row=row,
                manual_clips_dir=manual_clips_dir,
                clip_packages_dir=clip_packages_dir,
            )
        )

    _write_rows(manifest_csv, manifest_rows)
    package_created_count = sum(1 for row in manifest_rows if row.get("package_created") == "true")
    video_present_count = sum(1 for row in manifest_rows if row.get("video_present") == "true")
    metadata_valid = bool(manifest_rows) and all(row.get("metadata_valid") == "true" for row in manifest_rows)
    ok = len(manifest_rows) == 50 and package_created_count == 50 and video_present_count == 50 and metadata_valid

    print(f"PHASE34_SAV50_PACKAGE_MANIFEST={manifest_csv}")
    print(f"PHASE34_SAV50_PACKAGE_TOTAL={len(manifest_rows)}")
    print(f"PHASE34_SAV50_PACKAGE_CREATED_COUNT={package_created_count}")
    print(f"PHASE34_SAV50_PACKAGE_VIDEO_PRESENT_COUNT={video_present_count}")
    print(f"PHASE34_SAV50_PACKAGE_METADATA_VALID={_bool_text(metadata_valid)}")
    print(f"PHASE34_SAV50_PACKAGE_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _build_package(*, review_row: dict[str, str], manual_clips_dir: Path, clip_packages_dir: Path) -> dict[str, str]:
    clip_id = str(review_row.get("clip_id") or "").strip()
    source_video_id = str(review_row.get("source_video_id") or "").strip()
    package_dir = clip_packages_dir / clip_id
    package_dir.mkdir(parents=True, exist_ok=True)

    manual_clip_path = _resolve_manual_clip_path(review_row, manual_clips_dir)
    video_path = package_dir / "video.mp4"
    standardized_video_path = package_dir / "standardized_video.mp4"
    notes: list[str] = []

    if manual_clip_path.exists():
        _copy_file(manual_clip_path, video_path)
        _copy_file(manual_clip_path, standardized_video_path)
    else:
        notes.append("manual_clip_missing")

    duration_seconds = _probe_duration_seconds(video_path)
    recorded_at = _default_recorded_at()
    metadata = _build_metadata(
        review_row=review_row,
        package_dir=package_dir,
        video_path=video_path,
        standardized_video_path=standardized_video_path,
        duration_seconds=duration_seconds,
        recorded_at=recorded_at,
    )
    capture_metadata = _build_capture_metadata(
        review_row=review_row,
        package_dir=package_dir,
        video_path=video_path,
        standardized_video_path=standardized_video_path,
        duration_seconds=duration_seconds,
        recorded_at=recorded_at,
    )
    teacher_questions = {
        "status": "unavailable",
        "questions": [],
        "summary": {"question_count": 0},
        "reason": "sav_clip_no_teacher_transcript",
    }
    sav_source_annotation = _build_sav_source_annotation(review_row)
    human_review = _build_human_review(review_row)

    metadata_path = package_dir / "metadata.json"
    capture_metadata_path = package_dir / "capture_metadata.json"
    teacher_transcript_path = package_dir / "teacher_transcript.json"
    teacher_questions_path = package_dir / "teacher_questions.json"
    sav_source_annotation_path = package_dir / "sav_source_annotation.json"
    human_review_path = package_dir / "human_review.json"

    _write_json(metadata_path, metadata)
    _write_json(capture_metadata_path, capture_metadata)
    _write_json(teacher_transcript_path, [])
    _write_json(teacher_questions_path, teacher_questions)
    _write_json(sav_source_annotation_path, sav_source_annotation)
    _write_json(human_review_path, human_review)

    metadata_valid = _metadata_valid(metadata, capture_metadata)
    return {
        "dataset_order": str(review_row.get("dataset_order") or ""),
        "clip_id": clip_id,
        "source_video_id": source_video_id,
        "package_dir": str(package_dir),
        "video_path": str(video_path),
        "standardized_video_path": str(standardized_video_path),
        "metadata_path": str(metadata_path),
        "capture_metadata_path": str(capture_metadata_path),
        "teacher_transcript_path": str(teacher_transcript_path),
        "teacher_questions_path": str(teacher_questions_path),
        "sav_source_annotation_path": str(sav_source_annotation_path),
        "human_review_path": str(human_review_path),
        "manual_clip_path": str(manual_clip_path),
        "package_created": _bool_text(package_dir.exists()),
        "video_present": _bool_text(video_path.exists()),
        "standardized_video_present": _bool_text(standardized_video_path.exists()),
        "metadata_valid": _bool_text(metadata_valid),
        "final_phase34_category": str(review_row.get("final_phase34_category") or ""),
        "final_phase34_category_cn": str(review_row.get("final_phase34_category_cn") or ""),
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
        "data_mode": DATA_MODE,
        "is_demo": "false",
        "is_own_capture": "false",
        "notes": ";".join(notes),
    }


def _build_metadata(
    *,
    review_row: dict[str, str],
    package_dir: Path,
    video_path: Path,
    standardized_video_path: Path,
    duration_seconds: int,
    recorded_at: str,
) -> dict[str, Any]:
    clip_id = str(review_row.get("clip_id") or "")
    source_video_id = str(review_row.get("source_video_id") or "")
    return {
        "analysis_id": clip_id,
        "classroom_id": "SAV",
        "session_id": clip_id,
        "video_id": f"video_{clip_id}",
        "recorded_at": recorded_at,
        "duration_seconds": duration_seconds,
        "window_size_seconds": 10,
        "data_mode": DATA_MODE,
        "source_type": SOURCE_TYPE,
        "source_name": SOURCE_NAME,
        "is_demo": False,
        "is_own_capture": False,
        "session_type": "classroom_clip",
        "phase": PHASE,
        "clip_id": clip_id,
        "source_video_id": source_video_id,
        "source_path": str(video_path),
        "standardized_video_path": str(standardized_video_path),
        "browser_compatible": True,
        "transcode_status": "copied_from_manual_clip",
        "transcode_error": "",
        "students": {
            "estimated_student_count": _safe_int(review_row.get("person_count")),
        },
        "phase34_sav": {
            "clip_id": clip_id,
            "source_video_id": source_video_id,
            "final_phase34_category": str(review_row.get("final_phase34_category") or ""),
            "final_phase34_category_cn": str(review_row.get("final_phase34_category_cn") or ""),
        },
        "package_dir": str(package_dir),
    }


def _build_capture_metadata(
    *,
    review_row: dict[str, str],
    package_dir: Path,
    video_path: Path,
    standardized_video_path: Path,
    duration_seconds: int,
    recorded_at: str,
) -> dict[str, Any]:
    clip_id = str(review_row.get("clip_id") or "")
    return {
        "capture": {
            "device_id": "SAV_public_dataset",
            "classroom_id": "SAV",
            "session_id": clip_id,
            "captured_at": recorded_at,
            "package_dir": str(package_dir),
            "video_path": str(video_path),
            "standardized_video_path": str(standardized_video_path),
            "data_mode": DATA_MODE,
            "source_type": SOURCE_TYPE,
            "source_name": SOURCE_NAME,
            "is_demo": False,
            "is_own_capture": False,
        },
        "video": {
            "raw_video_path": str(video_path),
            "standardized_video_path": str(standardized_video_path),
            "duration_seconds": duration_seconds,
            "format": "mp4",
            "browser_compatible": True,
            "transcode_status": "copied_from_manual_clip",
            "transcode_error": "",
        },
    }


def _build_sav_source_annotation(row: dict[str, str]) -> dict[str, Any]:
    keys = (
        "clip_id",
        "source_video_id",
        "person_count",
        "stand_count",
        "raise_hand_count",
        "bend_count",
        "look_sideways_count",
        "talk_with_others_count",
        "answer_questions_count",
        "target_action_names",
    )
    return {key: _maybe_int(row.get(key)) for key in keys}


def _build_human_review(row: dict[str, str]) -> dict[str, str]:
    return {
        "final_phase34_category": str(row.get("final_phase34_category") or ""),
        "final_phase34_category_cn": str(row.get("final_phase34_category_cn") or ""),
        "manual_summary": str(row.get("manual_summary") or ""),
        "teaching_interpretation": str(row.get("teaching_interpretation") or ""),
    }


def _resolve_manual_clip_path(row: dict[str, str], manual_clips_dir: Path) -> Path:
    clip_id = str(row.get("clip_id") or "").strip()
    explicit = Path(str(row.get("manual_clip_path") or ""))
    if explicit.exists():
        return explicit.resolve()
    return (manual_clips_dir / f"{clip_id}.mp4").resolve()


def _copy_file(source: Path, target: Path) -> None:
    if source.resolve() == target.resolve():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _probe_duration_seconds(video_path: Path) -> int:
    if not video_path.exists():
        return 0
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


def _metadata_valid(metadata: dict[str, Any], capture_metadata: dict[str, Any]) -> bool:
    return (
        metadata.get("data_mode") == DATA_MODE
        and metadata.get("source_type") == SOURCE_TYPE
        and metadata.get("source_name") == SOURCE_NAME
        and metadata.get("is_demo") is False
        and metadata.get("is_own_capture") is False
        and metadata.get("session_type") == "classroom_clip"
        and metadata.get("phase") == PHASE
        and bool(metadata.get("clip_id"))
        and bool(metadata.get("source_video_id"))
        and isinstance(capture_metadata.get("capture"), dict)
    )


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
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in MANIFEST_FIELDS})


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_recorded_at() -> str:
    return datetime(2026, 5, 8, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_int(value: str | None) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def _maybe_int(value: str | None) -> int | str:
    text = str(value or "")
    try:
        return int(float(text))
    except ValueError:
        return text


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
