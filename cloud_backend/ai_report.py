"""Optional AI report summary helper for Phase 3.0."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict


def build_not_configured_summary() -> Dict[str, Any]:
    return {"enabled": False, "status": "not_configured", "content": ""}


def generate_ai_summary(report: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a single-lesson AI summary when explicitly configured."""
    if os.getenv("AI_REPORT_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        return build_not_configured_summary()
    provider = os.getenv("AI_REPORT_PROVIDER", "deepseek").strip().lower()
    api_key = os.getenv("AI_REPORT_API_KEY", "").strip()
    model = os.getenv("AI_REPORT_MODEL", "deepseek-chat").strip()
    timeout = int(os.getenv("AI_REPORT_TIMEOUT", "20"))
    if not api_key:
        return build_not_configured_summary()
    if provider != "deepseek":
        return {"enabled": True, "status": "failed", "content": "", "error": f"unsupported provider: {provider}"}

    structured = _structured_summary(report)
    prompt = (
        "你是一名课堂教学反馈专家。请基于以下结构化课堂报告，用中文写一段200-300字的综合评语，"
        "面向授课教师，语气专业、具体、建设性。不要编造输入中没有的数据。\n\n"
        + json.dumps(structured, ensure_ascii=False)
    )
    request_body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": "你只根据输入数据撰写课堂教学综合评语。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=request_body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            return {"enabled": True, "status": "failed", "content": "", "error": "empty response"}
        return {"enabled": True, "status": "success", "content": content}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        return {"enabled": True, "status": "failed", "content": "", "error": str(exc)}


def _structured_summary(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "basic": report.get("basic") or {},
        "scores": report.get("scores") or {},
        "question_analysis": report.get("question_analysis") or {},
        "stage_distribution": report.get("stage_distribution") or {},
        "highlights": report.get("highlights") or [],
        "risks": report.get("risks") or [],
        "recommendations": report.get("recommendations") or [],
        "risk_level": report.get("risk_level"),
        "dataset_source": report.get("dataset_source"),
    }
