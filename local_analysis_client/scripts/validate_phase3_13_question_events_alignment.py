from __future__ import annotations

import argparse
import json
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
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "asr_enriched_results"
    / ANALYSIS_ID
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.13 ASR question events and interaction alignment.")
    parser.add_argument("--transcript", type=Path, default=DEFAULT_TRANSCRIPT)
    parser.add_argument("--source-analysis", type=Path, default=DEFAULT_SOURCE_ANALYSIS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--analysis-id", default=ANALYSIS_ID)
    args = parser.parse_args()

    transcript_path = args.transcript.resolve()
    source_analysis_path = args.source_analysis.resolve()
    output_dir = args.output_dir.resolve()
    payload_path = output_dir / f"{args.analysis_id}.json"
    payload = read_json(payload_path)
    transcript = read_json(transcript_path)

    transcript_segments = transcript.get("segments") if isinstance(transcript.get("segments"), list) else []
    teacher = payload.get("teacher") if isinstance(payload.get("teacher"), dict) else {}
    question_events = teacher.get("question_events") if isinstance(teacher.get("question_events"), list) else []
    alignments = payload.get("interaction_alignment") if isinstance(payload.get("interaction_alignment"), list) else []
    response_detected_count = sum(1 for item in alignments if isinstance(item, dict) and item.get("response_detected"))
    payload_transcript = payload.get("transcript") if isinstance(payload.get("transcript"), list) else []
    evidence = payload.get("evidence_summary") if isinstance(payload.get("evidence_summary"), dict) else {}
    asr_quality = payload.get("asr_quality") if isinstance(payload.get("asr_quality"), dict) else {}
    payload_text = json.dumps(payload, ensure_ascii=False)
    summary_md = read_text(output_dir / "phase313_summary.md")

    no_diarization_claim = asr_quality.get("speaker_diarization") is False and "没有说话人分离" in summary_md
    overclaim_terms = ["精准教师识别", "自动教师身份识别", "teacher_identity_confidence\": \"high", "speaker_diarization\": true"]
    no_teacher_overclaim = not any(term in payload_text or term in summary_md for term in overclaim_terms)
    no_cloud_upload = bool((payload.get("phase313_asr_enrichment") or {}).get("no_cloud_upload")) and "没有上传云端" in summary_md
    ready = all(
        [
            transcript_path.exists(),
            len(transcript_segments) > 0,
            source_analysis_path.exists(),
            payload_path.exists(),
            len(question_events) > 0,
            len(alignments) > 0,
            response_detected_count > 0,
            len(payload_transcript) > 0,
            evidence.get("transcript_present") is True,
            bool(asr_quality),
            no_diarization_claim,
            no_teacher_overclaim,
            no_cloud_upload,
        ]
    )

    print(f"PHASE313_TRANSCRIPT_INPUT_PRESENT={bool_text(transcript_path.exists())}")
    print(f"PHASE313_TRANSCRIPT_SEGMENT_COUNT={len(transcript_segments)}")
    print(f"PHASE313_SOURCE_ANALYSIS_JSON_PRESENT={bool_text(source_analysis_path.exists())}")
    print(f"PHASE313_ASR_ENRICHED_PAYLOAD_PRESENT={bool_text(payload_path.exists())}")
    print(f"PHASE313_QUESTION_EVENTS_CREATED={bool_text(len(question_events) > 0)}")
    print(f"PHASE313_QUESTION_EVENT_COUNT={len(question_events)}")
    print(f"PHASE313_INTERACTION_ALIGNMENT_CREATED={bool_text(len(alignments) > 0)}")
    print(f"PHASE313_ALIGNMENT_COUNT={len(alignments)}")
    print(f"PHASE313_RESPONSE_DETECTED_COUNT={response_detected_count}")
    print(f"PHASE313_TRANSCRIPT_PRESENT_IN_PAYLOAD={bool_text(len(payload_transcript) > 0)}")
    print(f"PHASE313_EVIDENCE_TRANSCRIPT_PRESENT={bool_text(evidence.get('transcript_present') is True)}")
    print(f"PHASE313_ASR_QUALITY_PRESENT={bool_text(bool(asr_quality))}")
    print(f"PHASE313_NO_SPEAKER_DIARIZATION_CLAIM={bool_text(no_diarization_claim)}")
    print(f"PHASE313_NO_TEACHER_IDENTITY_OVERCLAIM={bool_text(no_teacher_overclaim)}")
    print(f"PHASE313_NO_CLOUD_UPLOAD={bool_text(no_cloud_upload)}")
    print(f"PHASE313_ASR_QUESTION_ALIGNMENT_READY={bool_text(ready)}")
    return 0 if ready else 1


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
