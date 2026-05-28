from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "teacher_questions_v1"
EXTRACTOR_NAME = "rule_based_question_extractor_v1"

QUESTION_MARKS = ("?", "\uFF1F")
OPEN_KEYWORDS = (
    "\u4E3A\u4EC0\u4E48",
    "\u5982\u4F55",
    "\u600E\u4E48",
    "\u4F60\u8BA4\u4E3A",
    "\u8BF4\u660E\u4E86\u4EC0\u4E48",
    "\u6709\u4EC0\u4E48\u5F71\u54CD",
    "\u8BF7\u89E3\u91CA",
    "\u4EC0\u4E48",
    "\u54EA\u4E2A",
)
CLOSED_KEYWORDS = (
    "\u662F\u5426",
    "\u662F\u4E0D\u662F",
    "\u5BF9\u4E0D\u5BF9",
    "\u80FD\u4E0D\u80FD",
    "\u6709\u6CA1\u6709",
    "\u662F\u5426\u6B63\u786E",
)
CHECK_KEYWORDS = (
    "\u660E\u767D\u4E86\u5417",
    "\u542C\u61C2\u4E86\u5417",
    "\u8FD8\u8BB0\u5F97\u5417",
    "\u8C01\u80FD\u56DE\u7B54",
    "\u4F1A\u4E0D\u4F1A",
)
WEAK_QUESTION_KEYWORDS = (
    "\u5417",
    "\u5462",
)
ALL_QUESTION_KEYWORDS = OPEN_KEYWORDS + CLOSED_KEYWORDS + CHECK_KEYWORDS
SENTENCE_SPLIT_PATTERN = re.compile(
    r"([^\u3002\uFF01\uFF1F!?\uFF1B;\n]+[\u3002\uFF01\uFF1F!?]?"
    r"|[^\u3002\uFF01\uFF1F!?\uFF1B;\n]+)"
)


@dataclass
class TeacherQuestionsResult:
    status: str
    question_count: int
    question_file: str
    error: str = ""


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_time(seconds: float) -> str:
    seconds_int = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds_int, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _display_time(start_sec: float, end_sec: float) -> str:
    return f"{_format_time(start_sec)}-{_format_time(end_sec)}"


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip()
    return " ".join(text.split())


def _sentence_candidates(text: str) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    candidates = [match.group(0).strip() for match in SENTENCE_SPLIT_PATTERN.finditer(normalized)]
    return [candidate for candidate in candidates if candidate]


def _has_question_signal(text: str) -> bool:
    if any(mark in text for mark in QUESTION_MARKS):
        return True
    if any(keyword in text for keyword in ALL_QUESTION_KEYWORDS):
        return True
    return any(keyword in text for keyword in WEAK_QUESTION_KEYWORDS)


def _question_type(text: str) -> str:
    if any(keyword in text for keyword in CHECK_KEYWORDS):
        return "check"
    if any(keyword in text for keyword in CLOSED_KEYWORDS):
        return "closed"
    if any(keyword in text for keyword in OPEN_KEYWORDS):
        return "open"
    return "unknown"


def _confidence(text: str) -> float:
    if any(mark in text for mark in QUESTION_MARKS):
        return 0.75
    if any(keyword in text for keyword in ALL_QUESTION_KEYWORDS):
        return 0.75
    if any(keyword in text for keyword in WEAK_QUESTION_KEYWORDS):
        return 0.60
    return 0.0


def _summary(questions: list[dict]) -> dict:
    return {
        "question_count": len(questions),
        "open_question_count": sum(1 for item in questions if item.get("question_type") == "open"),
        "closed_question_count": sum(1 for item in questions if item.get("question_type") == "closed"),
        "check_question_count": sum(1 for item in questions if item.get("question_type") == "check"),
        "has_questions": bool(questions),
    }


def _base_payload(
    capture_id: str,
    classroom_id: str,
    transcript_status: str,
    transcript_source: str,
    status: str,
    questions: list[dict],
    warnings: list[str],
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": capture_id,
        "classroom_id": classroom_id,
        "status": status,
        "source": {
            "transcript_status": transcript_status,
            "transcript_source": transcript_source,
            "extractor": EXTRACTOR_NAME,
            "generated_at": _now_iso(),
        },
        "questions": questions,
        "summary": _summary(questions),
        "warnings": warnings,
    }


def _unavailable_payload(
    capture_id: str,
    classroom_id: str,
    transcript_status: str,
    transcript_source: str,
    warning: str,
) -> dict:
    return _base_payload(
        capture_id=capture_id,
        classroom_id=classroom_id,
        transcript_status=transcript_status or "unavailable",
        transcript_source=transcript_source or "unavailable",
        status="unavailable",
        questions=[],
        warnings=[warning],
    )


def extract_teacher_questions(transcript: list[dict]) -> list[dict]:
    questions: list[dict] = []
    for segment in transcript:
        text = _normalize_text(segment.get("text"))
        if not text:
            continue
        start_sec = _safe_float(segment.get("start_sec"))
        end_sec = max(start_sec, _safe_float(segment.get("end_sec"), start_sec))
        candidates = _sentence_candidates(text) or [text]
        for candidate in candidates:
            candidate = _normalize_text(candidate)
            if not candidate or not _has_question_signal(candidate):
                continue
            question_index = len(questions) + 1
            questions.append(
                {
                    "question_id": f"q_{question_index:03d}",
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "display_time": _display_time(start_sec, end_sec),
                    "text": candidate,
                    "question_type": _question_type(candidate),
                    "confidence": _confidence(candidate),
                    "source": "rule_from_transcript",
                    "stage_hint": "unknown",
                }
            )
    return questions


def build_teacher_questions(
    transcript_path: Path,
    teacher_questions_path: Path,
    capture_id: str,
    classroom_id: str,
    transcript_status: str = "unavailable",
    transcript_source: str = "unavailable",
) -> TeacherQuestionsResult:
    transcript_path = Path(transcript_path)
    teacher_questions_path = Path(teacher_questions_path)

    if not transcript_path.exists():
        payload = _unavailable_payload(
            capture_id,
            classroom_id,
            transcript_status,
            transcript_source,
            "teacher_transcript_missing",
        )
        _write_json(teacher_questions_path, payload)
        return TeacherQuestionsResult("unavailable", 0, str(teacher_questions_path), "teacher_transcript_missing")

    try:
        transcript = _load_json(transcript_path)
    except Exception as exc:
        payload = _unavailable_payload(
            capture_id,
            classroom_id,
            transcript_status,
            transcript_source,
            "teacher_transcript_invalid",
        )
        _write_json(teacher_questions_path, payload)
        return TeacherQuestionsResult("unavailable", 0, str(teacher_questions_path), f"teacher_transcript_invalid:{exc}")

    if not isinstance(transcript, list):
        payload = _unavailable_payload(
            capture_id,
            classroom_id,
            transcript_status,
            transcript_source,
            "teacher_transcript_not_array",
        )
        _write_json(teacher_questions_path, payload)
        return TeacherQuestionsResult("unavailable", 0, str(teacher_questions_path), "teacher_transcript_not_array")

    if not transcript:
        payload = _unavailable_payload(
            capture_id,
            classroom_id,
            transcript_status,
            transcript_source,
            "teacher_transcript_empty",
        )
        _write_json(teacher_questions_path, payload)
        return TeacherQuestionsResult("unavailable", 0, str(teacher_questions_path), "teacher_transcript_empty")

    questions = extract_teacher_questions(transcript)
    if questions:
        payload = _base_payload(
            capture_id=capture_id,
            classroom_id=classroom_id,
            transcript_status=transcript_status,
            transcript_source=transcript_source,
            status="available",
            questions=questions,
            warnings=[],
        )
        _write_json(teacher_questions_path, payload)
        return TeacherQuestionsResult("available", len(questions), str(teacher_questions_path), "")

    payload = _base_payload(
        capture_id=capture_id,
        classroom_id=classroom_id,
        transcript_status=transcript_status,
        transcript_source=transcript_source,
        status="unavailable",
        questions=[],
        warnings=["no_teacher_questions_detected"],
    )
    _write_json(teacher_questions_path, payload)
    return TeacherQuestionsResult("unavailable", 0, str(teacher_questions_path), "no_teacher_questions_detected")
