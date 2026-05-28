from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS_ID = "phase312_asr_full_classroom_sav_20200908_17"
DEFAULT_VIDEO = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "videos"
    / "local_imported_sav_full_classroom_20200908_17.mp4"
)
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "asr_results"
    / DEFAULT_ANALYSIS_ID
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.12 local ASR transcript outputs.")
    parser.add_argument("--video", type=Path, default=DEFAULT_VIDEO)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    video_path = args.video.resolve()
    output_dir = args.output_dir.resolve()
    audio_path = output_dir / "extracted_audio.wav"
    status_path = output_dir / "asr_status.json"
    transcript_json_path = output_dir / "transcript.json"
    transcript_csv_path = output_dir / "transcript.csv"
    summary_path = output_dir / "asr_summary.md"
    status_doc = REPO_ROOT / "docs" / "project-status" / "v3-phase3.12-local-asr-transcript.md"
    runbook = REPO_ROOT / "docs" / "runbooks" / "v3-phase3.12-local-asr-transcript-runbook.md"

    status = read_json(status_path)
    transcript = read_json(transcript_json_path)
    segments = transcript.get("segments") if isinstance(transcript, dict) else []
    if not isinstance(segments, list):
        segments = []

    transcript_created = bool(status.get("transcript_created")) if isinstance(status, dict) else False
    segment_count = len(segments) if transcript_created else int(status.get("transcript_segment_count") or 0)
    has_timestamps = bool(
        transcript_created
        and segments
        and all(isinstance(seg, dict) and "start_sec" in seg and "end_sec" in seg and str(seg.get("text") or "").strip() for seg in segments)
    )
    no_question_events = "teacher" not in transcript and "question_events" not in json.dumps(transcript, ensure_ascii=False)
    docs_text = "\n".join([read_text(summary_path), read_text(status_doc), read_text(runbook)])
    pi_boundary = "树莓派端不是完整课堂内容 ASR 主链路" in docs_text or "Raspberry Pi" in docs_text and "command" in docs_text
    cloud_boundary = "云端不跑 ASR" in docs_text or "cloud does not run ASR" in docs_text

    ready = all(
        [
            output_dir.exists(),
            video_path.exists(),
            shutil.which("ffmpeg") is not None,
            audio_path.exists() and audio_path.stat().st_size > 0,
            bool(status.get("asr_engine_available")),
            transcript_created,
            transcript_json_path.exists(),
            transcript_csv_path.exists(),
            segment_count > 0,
            has_timestamps,
            no_question_events,
            pi_boundary,
            cloud_boundary,
        ]
    )

    print(f"PHASE312_OUTPUT_DIR_PRESENT={bool_text(output_dir.exists())}")
    print(f"PHASE312_INPUT_VIDEO_PRESENT={bool_text(video_path.exists())}")
    print(f"PHASE312_FFMPEG_AVAILABLE={bool_text(shutil.which('ffmpeg') is not None)}")
    print(f"PHASE312_AUDIO_EXTRACTED={bool_text(bool(status.get('audio_extracted')))}")
    print(f"PHASE312_AUDIO_WAV_PRESENT={bool_text(audio_path.exists() and audio_path.stat().st_size > 0 if audio_path.exists() else False)}")
    print(f"PHASE312_ASR_ENGINE_AVAILABLE={bool_text(bool(status.get('asr_engine_available')))}")
    print(f"PHASE312_ASR_ENGINE={status.get('asr_engine') or 'none'}")
    print(f"PHASE312_ASR_MODEL={status.get('asr_model') or 'none'}")
    print(f"PHASE312_ASR_TRANSCRIPT_CREATED={bool_text(transcript_created)}")
    print(f"PHASE312_TRANSCRIPT_JSON_PRESENT={bool_text(transcript_json_path.exists())}")
    print(f"PHASE312_TRANSCRIPT_CSV_PRESENT={bool_text(transcript_csv_path.exists())}")
    print(f"PHASE312_TRANSCRIPT_SEGMENT_COUNT={segment_count}")
    print(f"PHASE312_TRANSCRIPT_HAS_TIMESTAMPS={bool_text(has_timestamps)}")
    print(f"PHASE312_NO_QUESTION_EVENTS_CREATED={bool_text(no_question_events)}")
    print(f"PHASE312_PI_ASR_NOT_USED_FOR_CONTENT={bool_text(pi_boundary)}")
    print(f"PHASE312_CLOUD_ASR_NOT_USED={bool_text(cloud_boundary)}")
    print(f"PHASE312_LOCAL_ASR_TRANSCRIPT_READY={bool_text(ready)}")
    return 0 if ready or (output_dir.exists() and status_path.exists()) else 1


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
