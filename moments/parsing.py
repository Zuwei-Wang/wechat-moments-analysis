from __future__ import annotations

from typing import Any

from .constants import (
    AUDIENCE_TYPE_PROFILE,
    CONTENT_BASELINE,
    COMPLEXITY_MAP,
    POSTING_TIME_FACTOR,
    SENSITIVE_RISK_FACTOR,
    VISIBILITY_PLANS,
)
from .types import AudienceSegment, ValidationError


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"字段 {field_name} 不是有效数字") from exc


def _to_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise ValidationError(f"字段 {field_name} 不是有效布尔值")


def parse_payload(
    payload: dict[str, Any],
) -> tuple[str, str, list[str], list[AudienceSegment], list[str], str, str]:
    content_type = payload.get("contentType", "")
    if content_type not in CONTENT_BASELINE:
        raise ValidationError("内容类型不合法")

    posting_time = payload.get("postingTime", "daytime")
    if posting_time not in POSTING_TIME_FACTOR:
        raise ValidationError("发布时间不合法")

    sensitive_tags = payload.get("sensitiveTags", [])
    if not isinstance(sensitive_tags, list):
        raise ValidationError("敏感信息格式错误")
    for tag in sensitive_tags:
        if tag not in SENSITIVE_RISK_FACTOR:
            raise ValidationError(f"未知敏感标签: {tag}")

    raw_segments = payload.get("audiences", [])
    if not isinstance(raw_segments, list) or not raw_segments:
        raise ValidationError("请至少填写一个受众")

    raw_blocked_names = payload.get("blockedAudienceNames", [])
    if raw_blocked_names is None:
        raw_blocked_names = []
    if not isinstance(raw_blocked_names, list):
        raise ValidationError("屏蔽人群格式错误")
    blocked_names = [str(name).strip() for name in raw_blocked_names if str(name).strip()]

    selected_visibility_plan = str(payload.get("selectedVisibilityPlan", "all_visible"))
    if selected_visibility_plan not in VISIBILITY_PLANS:
        raise ValidationError("可见方案不合法")

    copy_text = str(payload.get("copyText", "")).strip()
    if len(copy_text) > 1000:
        raise ValidationError("文案长度不能超过 1000 字")

    segments: list[AudienceSegment] = []
    ratio_sum = 0.0
    for idx, segment in enumerate(raw_segments, start=1):
        name = str(segment.get("name", "")).strip()
        if not name:
            raise ValidationError(f"第 {idx} 行受众名称不能为空")

        ratio = _to_float(segment.get("ratio"), f"audience[{idx}].ratio")
        audience_type = str(segment.get("audienceType", "classmate_colleague"))
        complexity = str(segment.get("complexity", "medium"))
        in_group_raw = segment.get("inGroup", segment.get("isFriend", True))
        in_group = _to_bool(in_group_raw, f"audience[{idx}].inGroup")

        if ratio < 0:
            raise ValidationError(f"第 {idx} 行占比不能小于 0")
        if audience_type not in AUDIENCE_TYPE_PROFILE:
            raise ValidationError(f"第 {idx} 行受众类型不合法")
        if complexity not in COMPLEXITY_MAP:
            raise ValidationError(f"第 {idx} 行关系复杂度不合法")

        ratio_sum += ratio
        segments.append(
            AudienceSegment(
                name=name,
                ratio=ratio,
                audience_type=audience_type,
                complexity=complexity,
                in_group=in_group,
            )
        )

    if ratio_sum <= 0:
        raise ValidationError("受众占比总和必须大于 0")

    return (
        content_type,
        posting_time,
        sensitive_tags,
        segments,
        blocked_names,
        selected_visibility_plan,
        copy_text,
    )
