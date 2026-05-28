"""请求与响应模型。"""
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
    """课堂交互窗口统计结果。"""

    model_config = ConfigDict(extra="allow")

    window_id: str = Field(..., description="20 秒统计窗口唯一标识")
    classroom_id: Optional[str] = Field(default=None, description="教室标识")
    source_host: Optional[str] = Field(default=None, description="本地推理主机标识")
    started_at: Optional[datetime] = Field(default=None, description="窗口起始时间")
    ended_at: Optional[datetime] = Field(default=None, description="窗口结束时间")
    generated_at: Optional[datetime] = Field(default=None, description="结果生成时间")

    interaction_counts: Optional[Dict[str, Any]] = Field(
        default=None,
        description="交互统计，例如举手、起立、总事件数等",
    )
    grid_stats: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        default=None,
        description="3x3 网格区域统计",
    )
    deduplication: Optional[Dict[str, Any]] = Field(
        default=None,
        description="事件去重相关统计",
    )
    meta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="模型版本、窗口参数、来源设备等元信息",
    )

    @model_validator(mode="after")
    def validate_payload(self) -> "InteractionResultPayload":
        """做最小但有意义的结构校验。"""
        if not self.window_id.strip():
            raise ValueError("window_id 不能为空")
        return self


class ApiResponse(BaseModel):
    """统一响应结构。"""

    success: bool
    message: str
    request_id: str
    saved_path: Optional[str] = None
