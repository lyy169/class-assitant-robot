"""Classroom feedback JSON schema V1.1."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceInfo(BaseModel):
    source_kind: str
    source_path: str
    source_host: str


class TimeInfo(BaseModel):
    recorded_at: datetime
    generated_at: datetime
    duration_seconds: float = Field(..., ge=0)


class SummaryInfo(BaseModel):
    feedback_score: float = Field(..., ge=0, le=100)
    attention_score: float = Field(..., ge=0, le=100)
    response_score: float = Field(..., ge=0, le=100)
    teacher_question_count: int = Field(..., ge=0)
    avg_attention_ratio: float = Field(..., ge=0, le=1)
    response_success_rate: float = Field(..., ge=0, le=1)
    summary_text: str


class QuestionEvent(BaseModel):
    event_id: str
    start_sec: float = Field(..., ge=0)
    end_sec: float = Field(..., ge=0)
    text: str
    question_type: str

    @model_validator(mode="after")
    def validate_time_order(self) -> "QuestionEvent":
        if self.end_sec < self.start_sec:
            raise ValueError("question_events end_sec must be greater than or equal to start_sec")
        return self


class StageDistribution(BaseModel):
    exposition_ratio: float = Field(..., ge=0, le=1)
    question_ratio: float = Field(..., ge=0, le=1)
    discussion_ratio: float = Field(..., ge=0, le=1)
    summary_ratio: float = Field(..., ge=0, le=1)
    management_ratio: float = Field(..., ge=0, le=1)


class TeacherInfo(BaseModel):
    question_events: List[QuestionEvent]
    stage_distribution: StageDistribution


class ZoneStats(BaseModel):
    avg_attention_ratio: float = Field(..., ge=0, le=1)
    active_ratio: float = Field(..., ge=0, le=1)


class StudentZones(BaseModel):
    front: ZoneStats
    middle: ZoneStats
    back: ZoneStats


class StudentsInfo(BaseModel):
    estimated_student_count: int = Field(..., ge=0)
    hand_raise_event_count: int = Field(..., ge=0)
    zones: StudentZones


class TimelineInfo(BaseModel):
    window_size_seconds: float = Field(..., gt=0)
    attention_curve: List[float]
    heat_curve: List[float]
    activity_curve: List[float]

    @model_validator(mode="after")
    def validate_curve_lengths(self) -> "TimelineInfo":
        lengths = {
            len(self.attention_curve),
            len(self.heat_curve),
            len(self.activity_curve),
        }
        if len(lengths) != 1:
            raise ValueError("attention_curve, heat_curve, and activity_curve must have the same length")
        return self


class InteractionResultPayload(BaseModel):
    """Classroom feedback JSON payload V1.1."""

    model_config = ConfigDict(extra="allow")

    schema_version: str
    analysis_id: str
    classroom_id: str
    video_id: str
    source: SourceInfo
    time: TimeInfo
    summary: SummaryInfo
    teacher: TeacherInfo
    students: StudentsInfo
    timeline: TimelineInfo

    @model_validator(mode="after")
    def validate_payload(self) -> "InteractionResultPayload":
        if self.schema_version != "v1.1":
            raise ValueError("schema_version must be v1.1")
        if not self.analysis_id.strip():
            raise ValueError("analysis_id cannot be empty")
        if not self.classroom_id.strip():
            raise ValueError("classroom_id cannot be empty")
        if not self.video_id.strip():
            raise ValueError("video_id cannot be empty")
        return self


class ApiResponse(BaseModel):
    success: bool
    message: str
    request_id: str
    saved_path: Optional[str] = None
