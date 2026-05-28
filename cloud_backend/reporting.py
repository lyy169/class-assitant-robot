"""Rule-based classroom report helpers for Phase 3.0."""
from __future__ import annotations

from typing import Any, Dict, List


def build_rule_report(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Generate deterministic highlights, risks, recommendations, and risk level."""
    score = _number(metrics.get("score"))
    attention = _number(metrics.get("attention_score"))
    activity = _number(metrics.get("activity_score"))
    question_count = int(_number(metrics.get("question_count")))
    response_rate = _ratio(metrics.get("response_rate"))
    management_ratio = _ratio(metrics.get("management_ratio"))
    issue_count = int(_number(metrics.get("issue_count")))

    highlights: List[str] = []
    risks: List[str] = []
    recommendations: List[str] = []

    if score >= 85:
        highlights.append("本节课综合表现较好，课堂反馈得分处于较高水平。")
    if attention >= 80:
        highlights.append("学生注意力整体保持较稳定，可继续保持当前课堂节奏。")
    if activity >= 70:
        highlights.append("课堂活跃度较好，说明学生参与行为较充分。")
    if response_rate >= 0.7:
        highlights.append("教师提问后的响应情况较好，学生回应较积极。")

    if attention and attention < 60:
        risks.append("学生注意力水平偏低，课堂中可能存在走神或参与不足。")
        recommendations.append("建议增加互动节奏，在关键知识点后加入短问答或即时反馈。")
    if activity and activity < 45:
        risks.append("课堂活跃度偏低，学生主动参与行为不足。")
        recommendations.append("建议加入小组讨论、随堂练习或板演任务，提高学生参与密度。")
    if question_count < 3:
        risks.append("教师提问数量偏少，课堂互动触发点不足。")
        recommendations.append("建议围绕重点和易错点增加引导性问题。")
    if response_rate and response_rate < 0.45:
        risks.append("学生响应率偏低，提问后有效回应不足。")
        recommendations.append("建议延长等待时间，并通过追问帮助学生组织答案。")
    if management_ratio > 0.3:
        risks.append("课堂组织管理占比偏高，可能挤压讲授和互动时间。")
        recommendations.append("建议优化课堂规则和任务说明，减少重复组织管理耗时。")
    if issue_count >= 5:
        risks.append("课堂异常或问题事件较多，需要关注课堂秩序和参与度。")
        recommendations.append("建议复盘高频问题片段，针对座区或环节设计改进措施。")

    if not highlights:
        highlights.append("本节课已形成可分析的课堂行为数据，可结合趋势继续观察。")
    if not recommendations:
        recommendations.append("建议保持当前教学节奏，并持续关注注意力、活跃度和响应率的变化。")

    if score < 60 or attention < 55 or issue_count >= 8:
        risk_level = "high"
    elif score < 75 or attention < 70 or activity < 55 or risks:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "highlights": highlights[:4],
        "risks": risks[:5],
        "recommendations": _dedupe(recommendations)[:6],
        "risk_level": risk_level,
    }


def _number(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _ratio(value: Any) -> float:
    number = _number(value)
    return number / 100.0 if number > 1 else number


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
