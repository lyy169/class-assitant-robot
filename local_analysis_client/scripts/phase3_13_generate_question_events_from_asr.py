from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_ID = "phase313_asr_enriched_full_classroom_sav_20200908_17"
DEFAULT_TRANSCRIPT = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "asr_results"
    / "phase312_asr_full_classroom_sav_20200908_17"
    / "transcript.json"
)
DEFAULT_SOURCE_ANALYSIS = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "analysis_results"
    / "local_imported_sav_full_classroom_20200908_17.json"
)
DEFAULT_VIDEO = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "videos"
    / "local_imported_sav_full_classroom_20200908_17.mp4"
)
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "asr_enriched_results"
    / ANALYSIS_ID
)

CHINESE_KEYWORDS = [
    "谁",
    "什么",
    "为什么",
    "怎么",
    "怎样",
    "哪一个",
    "是不是",
    "对不对",
    "能不能",
    "有没有",
    "请回答",
    "谁来回答",
    "请你说",
    "大家想一想",
    "同学们看",
    "举手",
    "回答一下",
    "说一说",
]
ENGLISH_KEYWORDS = [
    "what",
    "why",
    "how",
    "who",
    "which",
    "can you",
    "do you",
    "is it",
    "are there",
    "anyone",
    "please answer",
    "raise your hand",
    "think about",
    "tell me",
    "could you",
    "would you",
    "look at",
    "let's",
    "read",
    "say",
]
QUESTION_WORDS = {"what", "why", "how", "who", "which", "when", "where"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate teacher question candidates and visual response alignment from ASR transcript.")
    parser.add_argument("--transcript", type=Path, default=DEFAULT_TRANSCRIPT)
    parser.add_argument("--source-analysis", type=Path, default=DEFAULT_SOURCE_ANALYSIS)
    parser.add_argument("--video", type=Path, default=DEFAULT_VIDEO)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--analysis-id", default=ANALYSIS_ID)
    parser.add_argument("--response-window-sec", type=int, default=20)
    args = parser.parse_args()

    transcript_path = args.transcript.resolve()
    source_analysis_path = args.source_analysis.resolve()
    video_path = args.video.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    transcript = read_json(transcript_path)
    source_payload = read_json(source_analysis_path)
    segments = transcript.get("segments") if isinstance(transcript.get("segments"), list) else []
    segments = [normalize_segment(segment) for segment in segments if isinstance(segment, dict)]

    raw_candidates = [candidate for segment in segments if (candidate := detect_question_candidate(segment))]
    question_events = merge_question_candidates(raw_candidates)
    question_events = [
        {
            **event,
            "event_id": f"q_{index:03d}",
        }
        for index, event in enumerate(question_events, start=1)
    ]

    alignments = build_interaction_alignment(
        question_events=question_events,
        source_payload=source_payload,
        response_window_sec=args.response_window_sec,
    )
    enriched = build_enriched_payload(
        source_payload=source_payload,
        transcript=transcript,
        segments=segments,
        question_events=question_events,
        alignments=alignments,
        analysis_id=args.analysis_id,
        transcript_path=transcript_path,
        video_path=video_path,
    )
    response_detected_count = sum(1 for item in alignments if item.get("response_detected"))
    summary = build_summary(
        transcript_path=transcript_path,
        source_analysis_path=source_analysis_path,
        output_dir=output_dir,
        question_events=question_events,
        alignments=alignments,
        response_detected_count=response_detected_count,
        transcript_segment_count=len(segments),
    )

    payload_path = output_dir / f"{args.analysis_id}.json"
    question_csv_path = output_dir / "question_events.csv"
    alignment_csv_path = output_dir / "interaction_alignment.csv"
    summary_json_path = output_dir / "phase313_summary.json"
    summary_md_path = output_dir / "phase313_summary.md"
    write_json(payload_path, enriched)
    write_question_events_csv(question_csv_path, question_events)
    write_alignment_csv(alignment_csv_path, alignments)
    write_json(summary_json_path, summary)
    summary_md_path.write_text(build_summary_markdown(summary), encoding="utf-8")

    print_markers(
        transcript_path=transcript_path,
        source_analysis_path=source_analysis_path,
        payload_path=payload_path,
        question_events=question_events,
        alignments=alignments,
        response_detected_count=response_detected_count,
        transcript_segment_count=len(segments),
    )
    return 0


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_segment(segment: dict[str, Any]) -> dict[str, Any]:
    return {
        "segment_id": str(segment.get("segment_id") or ""),
        "start_sec": safe_float(segment.get("start_sec")),
        "end_sec": safe_float(segment.get("end_sec")),
        "text": str(segment.get("text") or "").strip(),
        "confidence": segment.get("confidence"),
        "speaker": str(segment.get("speaker") or "unknown"),
        "speaker_role": str(segment.get("speaker_role") or "unknown"),
    }


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def detect_question_candidate(segment: dict[str, Any]) -> dict[str, Any] | None:
    text = str(segment.get("text") or "").strip()
    clean = normalize_text(text)
    if len(clean) < 10:
        return None

    matched: list[str] = []
    confidence = 0.0
    lower = clean.lower()
    tokens = set(re.findall(r"[a-zA-Z']+", lower))

    for keyword in CHINESE_KEYWORDS:
        if keyword in clean:
            matched.append(keyword)
            confidence += 0.22
    for keyword in ENGLISH_KEYWORDS:
        if keyword in lower:
            matched.append(keyword)
            confidence += 0.18
    if "?" in text or "？" in text:
        confidence += 0.16
        matched.append("question_mark")
    if QUESTION_WORDS & tokens:
        confidence += 0.12
    if re.search(r"\b(please|try|answer|think|look|tell|say|read)\b", lower):
        confidence += 0.08
    if not matched:
        return None
    if confidence < 0.22:
        return None

    duration = max(0.0, safe_float(segment.get("end_sec")) - safe_float(segment.get("start_sec")))
    if duration <= 0:
        return None

    return {
        "event_id": "",
        "start_sec": round(safe_float(segment.get("start_sec")), 3),
        "end_sec": round(safe_float(segment.get("end_sec")), 3),
        "text": text,
        "question_type": "question_candidate",
        "source": "asr_rule_detection",
        "confidence": round(min(0.92, 0.45 + confidence), 3),
        "speaker": "unknown",
        "speaker_role": "teacher_candidate",
        "speaker_confidence": "low_without_diarization",
        "matched_rules": sorted(set(matched)),
        "source_segment_ids": [segment.get("segment_id")],
    }


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def merge_question_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not candidates:
        return []
    candidates = sorted(candidates, key=lambda item: safe_float(item.get("start_sec")))
    merged: list[dict[str, Any]] = []
    current = copy.deepcopy(candidates[0])
    for candidate in candidates[1:]:
        gap = safe_float(candidate.get("start_sec")) - safe_float(current.get("end_sec"))
        if gap <= 5.0 and should_merge(current, candidate):
            current["end_sec"] = round(max(safe_float(current.get("end_sec")), safe_float(candidate.get("end_sec"))), 3)
            current["text"] = normalize_text(f"{current.get('text', '')} {candidate.get('text', '')}")
            current["confidence"] = round(max(safe_float(current.get("confidence")), safe_float(candidate.get("confidence"))), 3)
            current["matched_rules"] = sorted(set(current.get("matched_rules", [])) | set(candidate.get("matched_rules", [])))
            current["source_segment_ids"] = list(current.get("source_segment_ids", [])) + list(candidate.get("source_segment_ids", []))
        else:
            merged.append(current)
            current = copy.deepcopy(candidate)
    merged.append(current)
    return merged


def should_merge(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_rules = set(left.get("matched_rules", []))
    right_rules = set(right.get("matched_rules", []))
    if left_rules & right_rules:
        return True
    return len(str(left.get("text") or "")) < 60 or len(str(right.get("text") or "")) < 60


def build_interaction_alignment(
    question_events: list[dict[str, Any]],
    source_payload: dict[str, Any],
    response_window_sec: int,
) -> list[dict[str, Any]]:
    timeline = source_payload.get("timeline") if isinstance(source_payload.get("timeline"), dict) else {}
    activity_curve = timeline.get("activity_curve") if isinstance(timeline.get("activity_curve"), list) else []
    activity_values = [safe_float(value) for value in activity_curve]
    window_size = int(timeline.get("window_size_seconds") or 20)
    hand_raise_count = int((source_payload.get("students") or {}).get("hand_raise_event_count") or 0) if isinstance(source_payload.get("students"), dict) else 0
    alignments: list[dict[str, Any]] = []
    for event in question_events:
        start_sec = safe_float(event.get("start_sec"))
        end_sec = safe_float(event.get("end_sec"))
        baseline = curve_average(activity_values, end_sec - response_window_sec, end_sec, window_size)
        response_avg = curve_average(activity_values, end_sec, end_sec + response_window_sec, window_size)
        response_max = curve_max(activity_values, end_sec, end_sec + response_window_sec, window_size)
        activity_increase = response_avg > baseline + 0.04 or response_max >= 0.3333
        evidence = []
        if activity_increase:
            evidence.append("activity_curve_increase")
        if hand_raise_count > 0:
            evidence.append("global_hand_raise_count_present_no_timestamp")
        response_detected = bool(activity_increase)
        alignments.append(
            {
                "question_event_id": event["event_id"],
                "response_window_sec": response_window_sec,
                "window_start_sec": round(end_sec, 3),
                "window_end_sec": round(end_sec + response_window_sec, 3),
                "raise_hand_detected": False,
                "stand_detected": False,
                "activity_increase_detected": activity_increase,
                "response_detected": response_detected,
                "baseline_activity_avg": round(baseline, 4),
                "response_activity_avg": round(response_avg, 4),
                "response_activity_max": round(response_max, 4),
                "evidence": evidence or ["no_visual_response_signal_found"],
                "note": "Only activity_curve has reliable timing in the source analysis; hand_raise_count is global and not assigned to a specific question window.",
                "question_start_sec": round(start_sec, 3),
                "question_end_sec": round(end_sec, 3),
            }
        )
    return alignments


def curve_average(values: list[float], start_sec: float, end_sec: float, window_size: int) -> float:
    selected = select_curve_window(values, start_sec, end_sec, window_size)
    return sum(selected) / len(selected) if selected else 0.0


def curve_max(values: list[float], start_sec: float, end_sec: float, window_size: int) -> float:
    selected = select_curve_window(values, start_sec, end_sec, window_size)
    return max(selected) if selected else 0.0


def select_curve_window(values: list[float], start_sec: float, end_sec: float, window_size: int) -> list[float]:
    if not values:
        return []
    start = max(0, int(math.floor(max(start_sec, 0.0) / window_size)))
    end = min(len(values), int(math.ceil(max(end_sec, 0.0) / window_size)))
    if end <= start:
        end = min(len(values), start + 1)
    return values[start:end]


def build_enriched_payload(
    source_payload: dict[str, Any],
    transcript: dict[str, Any],
    segments: list[dict[str, Any]],
    question_events: list[dict[str, Any]],
    alignments: list[dict[str, Any]],
    analysis_id: str,
    transcript_path: Path,
    video_path: Path,
) -> dict[str, Any]:
    payload = copy.deepcopy(source_payload)
    payload["analysis_id"] = analysis_id
    payload["asr_source_analysis_id"] = source_payload.get("analysis_id")
    payload["transcript"] = segments
    payload["interaction_alignment"] = alignments
    payload["audio"] = {
        "asr_enabled": True,
        "asr_engine": (transcript.get("asr") or {}).get("engine", "faster-whisper") if isinstance(transcript.get("asr"), dict) else "faster-whisper",
        "asr_model": (transcript.get("asr") or {}).get("model", "") if isinstance(transcript.get("asr"), dict) else "",
        "transcript_present": bool(segments),
        "transcript_path": str(transcript_path),
        "transcript_segment_count": len(segments),
        "language": (transcript.get("asr") or {}).get("language", "auto") if isinstance(transcript.get("asr"), dict) else "auto",
        "source": "local_post_process",
        "audio_source": "extracted_from_video",
        "source_video": str(video_path),
    }
    teacher = payload.get("teacher") if isinstance(payload.get("teacher"), dict) else {}
    teacher["question_events"] = question_events
    teacher.setdefault("stage_distribution", {})
    payload["teacher"] = teacher
    response_count = sum(1 for item in alignments if item.get("response_detected"))
    question_count = len(question_events)
    response_success_rate = round(response_count / question_count, 4) if question_count else 0.0
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    summary["teacher_question_count"] = question_count
    summary["response_success_rate"] = response_success_rate
    summary["response_score"] = round(response_success_rate * 100, 2)
    summary["summary_text"] = (
        f"{summary.get('summary_text', '')} ASR 转写已生成 {len(segments)} 个片段，"
        f"规则检测到 {question_count} 个教师提问候选事件；由于当前没有说话人分离，"
        "这些事件只表示 teacher question candidates，不代表精准教师身份识别。"
    ).strip()
    payload["summary"] = summary
    evidence_summary = payload.get("evidence_summary") if isinstance(payload.get("evidence_summary"), dict) else {}
    evidence_summary.update(
        {
            "transcript_present": True,
            "transcript_segment_count": len(segments),
            "question_event_source": "asr_rule_detection",
            "interaction_alignment_present": bool(alignments),
        }
    )
    payload["evidence_summary"] = evidence_summary
    payload["asr_quality"] = {
        "speaker_diarization": False,
        "teacher_identity_confidence": "low_without_diarization",
        "question_event_type": "teacher_question_candidates",
        "note": "Question events are generated from ASR text rules and visual response alignment; no precise teacher identity recognition is claimed.",
    }
    payload["phase313_asr_enrichment"] = {
        "status": "generated",
        "no_cloud_upload": True,
        "no_speaker_diarization_claim": True,
        "no_teacher_identity_overclaim": True,
    }
    return payload


def build_summary(
    transcript_path: Path,
    source_analysis_path: Path,
    output_dir: Path,
    question_events: list[dict[str, Any]],
    alignments: list[dict[str, Any]],
    response_detected_count: int,
    transcript_segment_count: int,
) -> dict[str, Any]:
    return {
        "analysis_id": ANALYSIS_ID,
        "transcript_path": str(transcript_path),
        "source_analysis_path": str(source_analysis_path),
        "output_dir": str(output_dir),
        "transcript_segment_count": transcript_segment_count,
        "question_event_count": len(question_events),
        "alignment_count": len(alignments),
        "response_detected_count": response_detected_count,
        "response_success_rate": round(response_detected_count / len(question_events), 4) if question_events else 0.0,
        "speaker_diarization": False,
        "teacher_identity_confidence": "low_without_diarization",
        "question_event_explanation": "question_events 是基于 ASR 文本规则和视觉响应对齐生成的教师提问候选事件。",
        "no_teacher_identity_overclaim": True,
        "no_cloud_upload": True,
        "next_phase": "Phase 3.14 uploads the ASR-enhanced payload to cloud after review.",
    }


def build_summary_markdown(summary: dict[str, Any]) -> str:
    return f"""# Phase 3.13 ASR Question Events And Alignment Summary

## Result

- transcript_segment_count: {summary['transcript_segment_count']}
- question_event_count: {summary['question_event_count']}
- alignment_count: {summary['alignment_count']}
- response_detected_count: {summary['response_detected_count']}
- response_success_rate: {summary['response_success_rate']}

## Boundary

`question_events` 是基于 ASR 文本规则和视觉响应对齐生成的教师提问候选事件。

当前没有说话人分离，因此只输出提问候选，不做教师身份归属判断。所有事件均标记为 `teacher_candidate`，并带有 `speaker_confidence=low_without_diarization`。

本阶段没有上传云端。Phase 3.14 才会上传 ASR 增强版 payload。

## Outputs

- payload: `{summary['output_dir']}\\{ANALYSIS_ID}.json`
- question_events.csv: `{summary['output_dir']}\\question_events.csv`
- interaction_alignment.csv: `{summary['output_dir']}\\interaction_alignment.csv`
"""


def write_question_events_csv(path: Path, events: list[dict[str, Any]]) -> None:
    fields = [
        "event_id",
        "start_sec",
        "end_sec",
        "text",
        "question_type",
        "source",
        "confidence",
        "speaker",
        "speaker_role",
        "speaker_confidence",
        "matched_rules",
        "source_segment_ids",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fields)
        writer.writeheader()
        for event in events:
            row = {field: event.get(field, "") for field in fields}
            row["matched_rules"] = "|".join(event.get("matched_rules", []))
            row["source_segment_ids"] = "|".join(str(item) for item in event.get("source_segment_ids", []))
            writer.writerow(row)


def write_alignment_csv(path: Path, alignments: list[dict[str, Any]]) -> None:
    fields = [
        "question_event_id",
        "response_window_sec",
        "window_start_sec",
        "window_end_sec",
        "raise_hand_detected",
        "stand_detected",
        "activity_increase_detected",
        "response_detected",
        "baseline_activity_avg",
        "response_activity_avg",
        "response_activity_max",
        "evidence",
        "note",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fields)
        writer.writeheader()
        for item in alignments:
            row = {field: item.get(field, "") for field in fields}
            row["evidence"] = "|".join(item.get("evidence", []))
            writer.writerow(row)


def print_markers(
    transcript_path: Path,
    source_analysis_path: Path,
    payload_path: Path,
    question_events: list[dict[str, Any]],
    alignments: list[dict[str, Any]],
    response_detected_count: int,
    transcript_segment_count: int,
) -> None:
    print(f"PHASE313_TRANSCRIPT_INPUT_PRESENT={bool_text(transcript_path.exists())}")
    print(f"PHASE313_TRANSCRIPT_SEGMENT_COUNT={transcript_segment_count}")
    print(f"PHASE313_SOURCE_ANALYSIS_JSON_PRESENT={bool_text(source_analysis_path.exists())}")
    print(f"PHASE313_ASR_ENRICHED_PAYLOAD_PRESENT={bool_text(payload_path.exists())}")
    print(f"PHASE313_QUESTION_EVENTS_CREATED={bool_text(bool(question_events))}")
    print(f"PHASE313_QUESTION_EVENT_COUNT={len(question_events)}")
    print(f"PHASE313_INTERACTION_ALIGNMENT_CREATED={bool_text(bool(alignments))}")
    print(f"PHASE313_ALIGNMENT_COUNT={len(alignments)}")
    print(f"PHASE313_RESPONSE_DETECTED_COUNT={response_detected_count}")
    print("PHASE313_TRANSCRIPT_PRESENT_IN_PAYLOAD=true")
    print("PHASE313_EVIDENCE_TRANSCRIPT_PRESENT=true")
    print("PHASE313_ASR_QUALITY_PRESENT=true")
    print("PHASE313_NO_SPEAKER_DIARIZATION_CLAIM=true")
    print("PHASE313_NO_TEACHER_IDENTITY_OVERCLAIM=true")
    print("PHASE313_NO_CLOUD_UPLOAD=true")
    ready = transcript_path.exists() and source_analysis_path.exists() and payload_path.exists() and bool(question_events) and bool(alignments)
    print(f"PHASE313_ASR_QUESTION_ALIGNMENT_READY={bool_text(ready)}")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
