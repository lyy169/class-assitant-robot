"""请求与响应模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
