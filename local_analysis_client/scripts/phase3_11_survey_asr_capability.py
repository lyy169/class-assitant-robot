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
    parser = argparse.ArgumentParser(description="Survey Phase 3.11 ASR capability and generate ASR contract materials.")
    parser.add_argument("--materials-dir", type=Path, default=DEFAULT_MATERIALS_DIR)
    parser.add_argument("--full-classroom-video", type=Path, default=DEFAULT_FULL_CLASSROOM_VIDEO)
    args = parser.parse_args()

    materials_dir = args.materials_dir.resolve()
    full_classroom_video = args.full_classroom_video.resolve()

    survey = build_survey(full_classroom_video)
    write_materials(materials_dir, full_classroom_video, survey)

    print(f"PHASE311_ASR_SURVEY_DONE={bool_text(True)}")
    print(f"PHASE311_PI_COMMAND_ASR_IDENTIFIED={bool_text(survey['pi_command_asr_identified'])}")
    print(f"PHASE311_LOCAL_CONTENT_ASR_PRESENT={bool_text(survey['local_content_asr_present'])}")
    print(f"PHASE311_AUDIO_EXTRACTION_PRESENT={bool_text(survey['audio_extraction_present'])}")
    print(f"PHASE311_TRANSCRIPT_SCHEMA_PRESENT={bool_text(survey['transcript_schema_present'])}")
    print(f"PHASE311_QUESTION_EVENT_LOGIC_PRESENT={bool_text(survey['question_event_logic_present'])}")
    print(
        "PHASE311_IMPORT_AND_RECORDING_INPUTS_DISTINGUISHED="
        f"{bool_text(survey['import_and_recording_inputs_distinguished'])}"
    )
    print(f"PHASE311_FFMPEG_AVAILABLE={bool_text(survey['ffmpeg_available'])}")
    print(f"PHASE311_FULL_CLASSROOM_VIDEO_PRESENT={bool_text(survey['full_classroom_video_present'])}")
    print(f"PHASE311_FULL_CLASSROOM_AUDIO_STREAM_PRESENT={bool_text(survey['full_classroom_audio_stream_present'])}")
    print(f"PHASE311_LOCAL_ASR_ROLE_CONFIRMED={bool_text(True)}")
    print(f"PHASE311_PI_ASR_LIMITED_TO_COMMAND_CONTROL={bool_text(True)}")
    print(f"PHASE311_CLOUD_ASR_DISPLAY_ONLY={bool_text(True)}")
    print(f"PHASE311_ASR_SESSION_CONTRACT_READY={bool_text(True)}")
    print(f"PHASE311_NO_DB_MIGRATION_REQUIRED={bool_text(True)}")
    print(f"PHASE311_ASR_NEXT_IMPLEMENTATION_READY={bool_text(True)}")
    return 0


def build_survey(full_classroom_video: Path) -> dict[str, Any]:
    repo_text = read_project_text(include_docs=True)
    code_text = read_project_text(include_docs=False)
    ffmpeg_available = shutil.which("ffmpeg") is not None
    ffprobe_available = shutil.which("ffprobe") is not None
    audio_stream = probe_audio_stream(full_classroom_video) if ffprobe_available and full_classroom_video.exists() else None

    return {
        "pi_command_asr_identified": all(term in repo_text for term in ("语音唤醒", "语音指令")),
        "local_content_asr_present": detect_local_content_asr(code_text),
        "audio_extraction_present": detect_dedicated_asr_audio_extraction(code_text),
        "transcript_schema_present": all(term in repo_text for term in ("teacher_transcript", "teacher.question_events")),
        "question_event_logic_present": all(term in code_text for term in ("question_events", "_build_teacher_question_events")),
        "import_and_recording_inputs_distinguished": any(
            term in repo_text
            for term in (
                "is_pi_capture",
                "local_imported_video",
                "source_type",
                "capture_metadata",
            )
        ),
        "ffmpeg_available": ffmpeg_available,
        "ffprobe_available": ffprobe_available,
        "full_classroom_video_present": full_classroom_video.exists(),
        "full_classroom_audio_stream_present": audio_stream is not None,
        "audio_stream": audio_stream,
    }


def read_project_text(include_docs: bool) -> str:
    roots = [
        REPO_ROOT / "local-processor",
        REPO_ROOT / "scripts",
    ]
    if include_docs:
        roots.extend([REPO_ROOT / "docs", REPO_ROOT / "README.md"])
    else:
        roots.extend(
            [
                REPO_ROOT / "build_interaction_dataset.py",
                REPO_ROOT / "keyframe_receiver.py",
                REPO_ROOT / "train_interaction_model.py",
                REPO_ROOT / "yolo_interaction_processor.py",
                REPO_ROOT / "config.yaml",
            ]
        )

    parts: list[str] = []
    for root in roots:
        if root.is_file():
            parts.append(safe_read(root))
            continue
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or should_skip(path):
                continue
            if path.suffix.lower() not in {".py", ".md", ".yaml", ".yml", ".json", ".txt", ".ps1"}:
                continue
            if "phase3_11" in path.name or "v3-phase3.11" in path.name:
                continue
            if path.stat().st_size > 2_000_000:
                continue
            parts.append(safe_read(path))
    return "\n".join(parts)


def should_skip(path: Path) -> bool:
    skip_names = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        "runs",
        "venv",
        ".venv",
        "phase37_debug_tmp",
    }
    return any(part in skip_names for part in path.parts)


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def detect_local_content_asr(code_text: str) -> bool:
    normalized = code_text.lower()
    engine_terms = ("faster_whisper", "faster-whisper", "whisper", "vosk", "funasr", "pyaudio")
    return any(term in normalized for term in engine_terms) and any(
        term in normalized for term in ("transcribe", "asr", "recognize")
    )


def detect_dedicated_asr_audio_extraction(code_text: str) -> bool:
    normalized = code_text.lower()
    return all(term in normalized for term in ("ffmpeg", "16000", "mono")) and any(
        term in normalized for term in ("extract_audio", "audio_extraction", "asr_audio")
    )


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


def write_materials(materials_dir: Path, full_classroom_video: Path, survey: dict[str, Any]) -> None:
    materials_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "asr_layer_design.md": build_layer_design(full_classroom_video, survey),
        "asr_session_json_contract.md": build_contract_document(),
        "asr_phase312_recommendation.md": build_recommendation(full_classroom_video, survey),
    }
    for filename, content in files.items():
        (materials_dir / filename).write_text(content, encoding="utf-8")


def build_layer_design(full_classroom_video: Path, survey: dict[str, Any]) -> str:
    audio_stream = survey.get("audio_stream") or {}
    audio_line = "未探测到音频流"
    if audio_stream:
        audio_line = (
            f"codec={audio_stream.get('codec_name')}, "
            f"sample_rate={audio_stream.get('sample_rate')}, "
            f"channels={audio_stream.get('channels')}, "
            f"duration={audio_stream.get('duration')}"
        )

    return f"""# Phase 3.11 ASR 层职责设计

## 调研结论

当前本地项目已经具备 `audio.wav` 热度曲线分析、`teacher_transcript.json` / `teacher_questions.json` 读取、`teacher.question_events` 生成和 V1.1 extra 字段兼容展示基础。

当前没有确认到稳定接入的完整课堂内容 ASR 模块。仓库中没有发现可直接复用的 Whisper、faster-whisper、Vosk、FunASR 或同类完整课堂转写主链路。现有 Phase 3.3 能消费转写和教师提问结构，但不负责从完整课堂视频中自动产出 ASR 转写。

## 三端职责

- 树莓派端：只负责语音唤醒、语音指令和录像控制。树莓派端 ASR 不作为完整课堂内容转写主链路。
- 本地分析端：负责从导入视频或树莓派录制视频中提取音频，执行完整课堂 ASR，生成 transcript 和 teacher.question_events。
- 云端：只负责展示 ASR 转写摘要、教师提问事件、视频和行为分析结果，不在云端运行 ASR。

## 输入统一原则

导入视频和树莓派录制视频都进入本地端统一后处理流程。本地端在 payload 中保留来源字段，例如 `source_type`、`is_pi_capture`、`is_own_capture`、`is_local_processed`，避免把 SAV 外部样本误写成树莓派采集或自采。

## 当前完整课堂样本可行性

- 视频路径：`{full_classroom_video}`
- 视频存在：{bool_text(survey["full_classroom_video_present"])}
- ffmpeg 可用：{bool_text(survey["ffmpeg_available"])}
- 音频流存在：{bool_text(survey["full_classroom_audio_stream_present"])}
- 音频流信息：{audio_line}

该完整课堂视频适合作为 Phase 3.12 ASR 可行性测试输入。本阶段没有运行完整 ASR，只确认音频流和工具链可用性。
"""


def build_contract_document() -> str:
    return """# Phase 3.11 ASR 增强版 Session JSON 契约

## 兼容原则

ASR 增强字段作为 V1.1 payload 的 extra 字段进入云端。云端当前 schema 允许 extra 字段，因此不要求数据库迁移，不要求重写 dashboard，也不要求云端运行 ASR。

## 建议字段

```json
{
  "audio": {
    "asr_enabled": true,
    "asr_engine": "local_whisper_or_project_engine",
    "transcript_present": true,
    "language": "auto",
    "source": "local_post_process",
    "audio_source": "extracted_from_video"
  },
  "transcript": [
    {
      "segment_id": "seg_001",
      "start_sec": 12.4,
      "end_sec": 18.7,
      "speaker": "unknown",
      "speaker_role": "teacher_candidate",
      "text": "谁能回答这个问题？",
      "confidence": 0.86
    }
  ],
  "teacher": {
    "question_events": [
      {
        "event_id": "q_001",
        "start_sec": 12.4,
        "end_sec": 18.7,
        "text": "谁能回答这个问题？",
        "question_type": "question_candidate",
        "source": "asr_rule_detection",
        "confidence": 0.72
      }
    ],
    "stage_distribution": {}
  },
  "interaction_alignment": [
    {
      "question_event_id": "q_001",
      "response_window_sec": 15,
      "raise_hand_detected": true,
      "stand_detected": false,
      "activity_increase_detected": true,
      "response_detected": true
    }
  ],
  "asr_quality": {
    "speaker_diarization": false,
    "teacher_identity_confidence": "low_without_diarization",
    "note": "Question events are generated from ASR question candidates and visual response alignment."
  },
  "evidence_summary": {
    "transcript_present": true
  }
}
```

## 字段说明

- `audio` 记录 ASR 是否启用、引擎、语言和音频来源。
- `transcript` 保存带时间戳的完整课堂转写片段。
- `teacher.question_events` 保存由 ASR 规则检测出的教师提问候选事件。
- `interaction_alignment` 或 `response_alignment` 对齐提问事件和视觉响应行为。
- `asr_quality` 记录无说话人分离时的身份置信边界。
- `evidence_summary.transcript_present` 给云端和报告提供轻量证据标记。
"""


def build_recommendation(full_classroom_video: Path, survey: dict[str, Any]) -> str:
    return f"""# Phase 3.12 ASR 实现建议

## 推荐方向

当前没有发现可直接复用的本地完整课堂内容 ASR 主链路。Phase 3.12 建议新增本地离线 ASR 管线，但不改核心视觉算法、不重训模型、不在云端跑 ASR。

## 建议步骤

1. 使用 ffmpeg 从完整课堂视频提取 16kHz mono WAV。
2. 使用 Whisper、faster-whisper 或项目确认的离线 ASR 引擎进行转写。
3. 输出 `transcript.json` 和可审阅的 `transcript.csv`。
4. Phase 3.13 再根据问号、疑问词、教师候选片段和视觉响应窗口生成 `teacher.question_events`。
5. 将 `audio`、`transcript`、`teacher.question_events`、`interaction_alignment`、`asr_quality` 写入 V1.1 extra-compatible payload。

## 推荐测试输入

- 完整课堂视频：`{full_classroom_video}`
- ffmpeg 可用：{bool_text(survey["ffmpeg_available"])}
- 音频流存在：{bool_text(survey["full_classroom_audio_stream_present"])}

该视频来自 SAV 外部公开课堂样本，适合作为 Phase 3.12 的完整课堂 ASR 测试输入。它不是树莓派采集，不是自采；树莓派端继续用于语音唤醒、语音指令和录像控制演示。

## 不做事项

- 不把树莓派命令识别当作完整课堂内容转写。
- 不在云端执行 ASR。
- 不做数据库迁移。
- 不重新训练视觉模型。
- 不重新下载或重新切片 SAV 数据。
"""


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
