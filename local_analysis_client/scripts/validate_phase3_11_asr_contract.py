from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATERIALS_DIR = REPO_ROOT.parent / "competition_materials"
DEFAULT_FULL_CLASSROOM_VIDEO = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "videos"
    / "local_imported_sav_full_classroom_20200908_17.mp4"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.11 ASR survey reports and session contract.")
    parser.add_argument("--materials-dir", type=Path, default=DEFAULT_MATERIALS_DIR)
    parser.add_argument("--full-classroom-video", type=Path, default=DEFAULT_FULL_CLASSROOM_VIDEO)
    args = parser.parse_args()

    materials_dir = args.materials_dir.resolve()
    full_classroom_video = args.full_classroom_video.resolve()

    layer = materials_dir / "asr_layer_design.md"
    contract = materials_dir / "asr_session_json_contract.md"
    recommendation = materials_dir / "asr_phase312_recommendation.md"

    layer_text = read_text(layer)
    contract_text = read_text(contract)
    recommendation_text = read_text(recommendation)
    all_text = "\n".join([layer_text, contract_text, recommendation_text])

    ffmpeg_available = shutil.which("ffmpeg") is not None
    audio_stream = probe_audio_stream(full_classroom_video) if full_classroom_video.exists() and shutil.which("ffprobe") else None

    survey_done = all(path.exists() for path in (layer, contract, recommendation))
    pi_command = all(term in all_text for term in ("语音唤醒", "语音指令", "录像控制"))
    local_content_asr_present = "当前没有确认到稳定接入的完整课堂内容 ASR 模块" not in all_text
    audio_extraction_present = "当前没有确认到稳定接入" not in all_text and "16kHz mono WAV" in all_text
    transcript_schema = all(term in contract_text for term in ("transcript", "segment_id", "start_sec", "end_sec"))
    question_logic = all(term in contract_text for term in ("teacher", "question_events", "asr_rule_detection"))
    inputs_distinguished = all(term in all_text for term in ("导入视频", "树莓派录制视频", "is_pi_capture"))
    local_role = "本地分析端" in all_text and "完整课堂 ASR" in all_text
    pi_limited = "树莓派端 ASR 不作为完整课堂内容转写主链路" in all_text
    cloud_display = "云端" in all_text and "不在云端运行 ASR" in all_text
    contract_ready = all(
        term in contract_text
        for term in (
            '"audio"',
            '"transcript"',
            '"question_events"',
            '"interaction_alignment"',
            '"asr_quality"',
            '"transcript_present"',
        )
    )
    no_db_migration = "不要求数据库迁移" in contract_text or "不做数据库迁移" in recommendation_text
    next_ready = all(term in recommendation_text for term in ("Phase 3.12", "ffmpeg", "Whisper", "transcript.json"))

    ok = all(
        [
            survey_done,
            pi_command,
            transcript_schema,
            question_logic,
            inputs_distinguished,
            ffmpeg_available,
            full_classroom_video.exists(),
            audio_stream is not None,
            local_role,
            pi_limited,
            cloud_display,
            contract_ready,
            no_db_migration,
            next_ready,
        ]
    )

    print(f"PHASE311_ASR_SURVEY_DONE={bool_text(survey_done)}")
    print(f"PHASE311_PI_COMMAND_ASR_IDENTIFIED={bool_text(pi_command)}")
    print(f"PHASE311_LOCAL_CONTENT_ASR_PRESENT={bool_text(local_content_asr_present)}")
    print(f"PHASE311_AUDIO_EXTRACTION_PRESENT={bool_text(audio_extraction_present)}")
    print(f"PHASE311_TRANSCRIPT_SCHEMA_PRESENT={bool_text(transcript_schema)}")
    print(f"PHASE311_QUESTION_EVENT_LOGIC_PRESENT={bool_text(question_logic)}")
    print(f"PHASE311_IMPORT_AND_RECORDING_INPUTS_DISTINGUISHED={bool_text(inputs_distinguished)}")
    print(f"PHASE311_FFMPEG_AVAILABLE={bool_text(ffmpeg_available)}")
    print(f"PHASE311_FULL_CLASSROOM_VIDEO_PRESENT={bool_text(full_classroom_video.exists())}")
    print(f"PHASE311_FULL_CLASSROOM_AUDIO_STREAM_PRESENT={bool_text(audio_stream is not None)}")
    print(f"PHASE311_LOCAL_ASR_ROLE_CONFIRMED={bool_text(local_role)}")
    print(f"PHASE311_PI_ASR_LIMITED_TO_COMMAND_CONTROL={bool_text(pi_limited)}")
    print(f"PHASE311_CLOUD_ASR_DISPLAY_ONLY={bool_text(cloud_display)}")
    print(f"PHASE311_ASR_SESSION_CONTRACT_READY={bool_text(contract_ready)}")
    print(f"PHASE311_NO_DB_MIGRATION_REQUIRED={bool_text(no_db_migration)}")
    print(f"PHASE311_ASR_NEXT_IMPLEMENTATION_READY={bool_text(next_ready)}")
    return 0 if ok else 1


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def probe_audio_stream(video_path: Path) -> dict[str, Any] | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,channels,duration,bit_rate",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    streams = payload.get("streams") if isinstance(payload, dict) else None
    if not streams:
        return None
    stream = streams[0]
    return stream if isinstance(stream, dict) else None


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
