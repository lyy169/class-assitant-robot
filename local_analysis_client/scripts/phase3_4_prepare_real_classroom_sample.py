from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}
SOURCE_NAME = "local_real_classroom_sample"
SOURCE_TYPE = "own_real_classroom_session"
DATA_MODE = "local_real_classroom_session"

MANIFEST_FIELDS = (
    "sample_id",
    "sample_name",
    "source_video_path",
    "source_package_dir",
    "analysis_package_dir",
    "duration_seconds",
    "video_size_bytes",
    "classroom_id",
    "session_id",
    "recorded_at",
    "raspberry_pi_capture",
    "raspberry_pi_capture_note",
    "source_name",
    "source_type",
    "data_mode",
    "is_demo",
    "is_own_capture",
    "ready_for_analysis",
    "notes",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare one real full-classroom sample for Phase 3.4e.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    parser.add_argument("--source-video", type=Path, default=None)
    parser.add_argument("--min-duration-sec", type=int, default=120)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    reports_dir = sample_root / "reports"
    analysis_results_dir = sample_root / "analysis_results"
    packages_dir = sample_root / "packages"
    manifest_csv = reports_dir / "real_classroom_sample_manifest.csv"

    for path in (sample_root, reports_dir, analysis_results_dir, packages_dir):
        path.mkdir(parents=True, exist_ok=True)

    candidates = _discover_candidates(
        sample_root=sample_root,
        explicit_source_video=args.source_video,
        min_duration_sec=args.min_duration_sec,
    )
    selected = candidates[0] if candidates else None
    manifest_rows: list[dict[str, str]] = []
    if selected is not None:
        manifest_rows.append(_build_manifest_row(selected=selected, packages_dir=packages_dir))
    _write_rows(manifest_csv, manifest_rows)

    video_present = bool(selected is not None and Path(selected["video_path"]).exists())
    ready = bool(manifest_rows and manifest_rows[0].get("ready_for_analysis") == "true")
    print(f"PHASE34_REAL_CLASSROOM_WORKSPACE={sample_root}")
    print(f"PHASE34_REAL_CLASSROOM_REPORTS_DIR={reports_dir}")
    print(f"PHASE34_REAL_CLASSROOM_ANALYSIS_RESULTS_DIR={analysis_results_dir}")
    print(f"PHASE34_REAL_CLASSROOM_MANIFEST={manifest_csv}")
    print(f"PHASE34_REAL_CLASSROOM_VIDEO_PRESENT={_bool_text(video_present)}")
    print(f"PHASE34_REAL_CLASSROOM_READY_FOR_ANALYSIS={_bool_text(ready)}")
    if selected is not None:
        print(f"PHASE34_REAL_CLASSROOM_SELECTED_VIDEO={selected['video_path']}")
        print(f"PHASE34_REAL_CLASSROOM_DURATION_SECONDS={selected['duration_seconds']}")
    else:
        print(f"PHASE34_REAL_CLASSROOM_TODO=place_video_under_{sample_root}")
    return 0


def _discover_candidates(
    *,
    sample_root: Path,
    explicit_source_video: Path | None,
    min_duration_sec: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if explicit_source_video is not None:
        candidates.extend(_candidate_from_video(explicit_source_video.resolve(), origin="explicit_source_video"))

    if sample_root.exists():
        for path in sorted(sample_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
                continue
            if any(part.lower() in {"reports", "analysis_results", "packages"} for part in path.relative_to(sample_root).parts):
                continue
            candidates.extend(_candidate_from_video(path.resolve(), origin="sample_root_video"))

    delivery_root = REPO_ROOT / "captures_local_delivery"
    if delivery_root.exists():
        for video_path in sorted(delivery_root.rglob("video.mp4")):
            lowered = str(video_path).lower()
            if "classroom-demo" in lowered or "validation_skip" in lowered:
                continue
            candidates.extend(_candidate_from_video(video_path.resolve(), origin="existing_local_delivery"))

    complete_candidates = [item for item in candidates if int(item.get("duration_seconds") or 0) >= min_duration_sec]
    complete_candidates.sort(key=lambda item: _candidate_sort_key(item), reverse=True)
    return complete_candidates


def _candidate_from_video(video_path: Path, *, origin: str) -> list[dict[str, Any]]:
    if not video_path.exists():
        return []
    package_dir = video_path.parent
    metadata = _read_json(package_dir / "metadata.json")
    capture_metadata = _read_json(package_dir / "capture_metadata.json")
    duration = _probe_duration_seconds(video_path)
    if duration <= 0:
        duration = int(float(metadata.get("duration_seconds") or 0)) if isinstance(metadata, dict) else 0
    classroom_id = _first_text(metadata.get("classroom_id"), _nested(capture_metadata, "capture", "classroom_id"), "classroom")
    session_id = _first_text(metadata.get("session_id"), metadata.get("capture_id"), video_path.parent.name)
    recorded_at = _first_text(
        metadata.get("recorded_at"),
        metadata.get("started_at"),
        _nested(capture_metadata, "capture", "captured_at"),
        "",
    )
    raspberry, raspberry_note = _infer_raspberry_pi_capture(metadata, capture_metadata, video_path)
    return [
        {
            "video_path": str(video_path),
            "package_dir": str(package_dir) if (package_dir / "metadata.json").exists() else "",
            "origin": origin,
            "duration_seconds": int(duration),
            "video_size_bytes": video_path.stat().st_size,
            "classroom_id": classroom_id,
            "session_id": session_id,
            "recorded_at": recorded_at,
            "raspberry_pi_capture": raspberry,
            "raspberry_pi_capture_note": raspberry_note,
            "metadata": metadata if isinstance(metadata, dict) else {},
        }
    ]


def _build_manifest_row(*, selected: dict[str, Any], packages_dir: Path) -> dict[str, str]:
    source_video_path = Path(str(selected["video_path"])).resolve()
    source_package_dir = Path(str(selected.get("package_dir") or "")).resolve() if selected.get("package_dir") else None
    sample_id = _sample_id(selected)
    notes: list[str] = [str(selected.get("origin") or "")]
    if source_package_dir is not None and source_package_dir.exists():
        analysis_package_dir = source_package_dir
    else:
        analysis_package_dir = _create_standalone_package(
            source_video_path=source_video_path,
            packages_dir=packages_dir,
            sample_id=sample_id,
            selected=selected,
        )
        notes.append("standalone_package_created")

    return {
        "sample_id": sample_id,
        "sample_name": "Phase 3.4e actual full classroom sample",
        "source_video_path": str(source_video_path),
        "source_package_dir": str(source_package_dir) if source_package_dir else "",
        "analysis_package_dir": str(analysis_package_dir),
        "duration_seconds": str(int(selected.get("duration_seconds") or 0)),
        "video_size_bytes": str(int(selected.get("video_size_bytes") or 0)),
        "classroom_id": str(selected.get("classroom_id") or ""),
        "session_id": str(selected.get("session_id") or ""),
        "recorded_at": str(selected.get("recorded_at") or ""),
        "raspberry_pi_capture": str(selected.get("raspberry_pi_capture") or "unknown"),
        "raspberry_pi_capture_note": str(selected.get("raspberry_pi_capture_note") or ""),
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
        "data_mode": DATA_MODE,
        "is_demo": "false",
        "is_own_capture": "true",
        "ready_for_analysis": _bool_text(source_video_path.exists() and analysis_package_dir.exists()),
        "notes": ";".join(note for note in notes if note),
    }


def _create_standalone_package(
    *,
    source_video_path: Path,
    packages_dir: Path,
    sample_id: str,
    selected: dict[str, Any],
) -> Path:
    package_dir = packages_dir / sample_id
    package_dir.mkdir(parents=True, exist_ok=True)
    target_video = package_dir / "video.mp4"
    if source_video_path.resolve() != target_video.resolve():
        shutil.copy2(source_video_path, target_video)
    metadata = {
        "analysis_id": sample_id,
        "classroom_id": selected.get("classroom_id") or "real_classroom",
        "session_id": selected.get("session_id") or sample_id,
        "recorded_at": selected.get("recorded_at") or "",
        "duration_seconds": int(selected.get("duration_seconds") or 0),
        "source_kind": "captured_video",
        "source_path": str(target_video),
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
        "data_mode": DATA_MODE,
        "is_demo": False,
        "is_own_capture": True,
    }
    capture_metadata = {
        "capture": {
            "device_id": "unknown",
            "classroom_id": metadata["classroom_id"],
            "captured_at": metadata["recorded_at"],
            "video_path": str(target_video),
            "source_name": SOURCE_NAME,
            "source_type": SOURCE_TYPE,
            "data_mode": DATA_MODE,
            "is_demo": False,
            "is_own_capture": True,
        },
        "video": {"raw_video_path": str(target_video), "duration_seconds": metadata["duration_seconds"]},
    }
    _write_json(package_dir / "metadata.json", metadata)
    _write_json(package_dir / "capture_metadata.json", capture_metadata)
    _write_json(package_dir / "teacher_transcript.json", [])
    _write_json(
        package_dir / "teacher_questions.json",
        {"status": "unavailable", "questions": [], "summary": {"question_count": 0}, "reason": "real_classroom_transcript_unavailable"},
    )
    return package_dir


def _sample_id(selected: dict[str, Any]) -> str:
    classroom_id = _safe_id(str(selected.get("classroom_id") or "real_classroom"))
    session_id = _safe_id(str(selected.get("session_id") or "session"))
    return f"phase34e_{classroom_id}_{session_id}"


def _candidate_sort_key(item: dict[str, Any]) -> tuple[int, int, int]:
    origin_score = {"sample_root_video": 3, "explicit_source_video": 2, "existing_local_delivery": 1}.get(str(item.get("origin")), 0)
    return (origin_score, int(item.get("duration_seconds") or 0), int(item.get("video_size_bytes") or 0))


def _infer_raspberry_pi_capture(metadata: Any, capture_metadata: Any, video_path: Path) -> tuple[str, str]:
    text = " ".join(
        str(value)
        for value in (
            metadata.get("source_host") if isinstance(metadata, dict) else "",
            metadata.get("device_id") if isinstance(metadata, dict) else "",
            _nested(capture_metadata, "capture", "device_id"),
            _nested(capture_metadata, "capture", "device_name"),
            str(video_path),
        )
    ).lower()
    if "raspberry" in text or "pi-" in text or "pi_" in text or "raspberrypi" in text:
        return "true", "inferred_from_metadata_or_path"
    return "unknown", "not_confirmed_by_metadata"


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


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in MANIFEST_FIELDS})


def _nested(payload: Any, *keys: str) -> str:
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return str(current or "")


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
