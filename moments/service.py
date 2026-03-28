from __future__ import annotations

from typing import Any

from .copywriting import analyze_copy_text
from .history import save_analysis_record
from .personalization import get_profile
from .evaluation import build_score_explanation, evaluate
from .parsing import parse_payload
from .suggestions import build_action_suggestions
from .types import ValidationError
from .visibility import segments_by_visibility_plan, simulate_visibility, visibility_plan_label


def evaluate_request(payload: dict[str, Any]) -> dict[str, Any]:
    (
        content_type,
        posting_time,
        manual_sensitive_tags,
        segments,
        blocked_names,
        selected_visibility_plan,
        copy_text,
    ) = parse_payload(payload)

    copy_analysis = analyze_copy_text(copy_text) if copy_text else None
    auto_sensitive_tags = copy_analysis["detectedTags"] if copy_analysis else []
    sensitive_tags = list(dict.fromkeys([*manual_sensitive_tags, *auto_sensitive_tags]))
    copy_risk_dim_boost = copy_analysis["dimensionBoost"] if copy_analysis else None
    profile = get_profile()
    benefit_multiplier = float(profile["benefitMultiplier"])
    risk_multiplier = float(profile["riskMultiplier"])

    active_segments = segments_by_visibility_plan(selected_visibility_plan, segments, blocked_names)
    if not active_segments:
        raise ValidationError("当前可见方案下没有可见受众，请调整分组或屏蔽设置")

    result = evaluate(
        content_type,
        posting_time,
        sensitive_tags,
        active_segments,
        risk_dim_boost=copy_risk_dim_boost,
        benefit_multiplier=benefit_multiplier,
        risk_multiplier=risk_multiplier,
    )
    visibility_simulation = simulate_visibility(
        content_type,
        posting_time,
        sensitive_tags,
        segments,
        blocked_names,
        risk_dim_boost=copy_risk_dim_boost,
        benefit_multiplier=benefit_multiplier,
        risk_multiplier=risk_multiplier,
    )

    result["visibilitySimulation"] = visibility_simulation
    result["meta"]["selectedVisibilityPlan"] = selected_visibility_plan
    result["meta"]["selectedVisibilityPlanLabel"] = visibility_plan_label(selected_visibility_plan)

    result["scoreExplanation"] = build_score_explanation(
        content_type=content_type,
        posting_time=posting_time,
        sensitive_tags=sensitive_tags,
        all_segments=segments,
        active_segments=active_segments,
        selected_visibility_plan=selected_visibility_plan,
        details=result["details"],
        risk_dim_boost=copy_risk_dim_boost,
        benefit_multiplier=benefit_multiplier,
        risk_multiplier=risk_multiplier,
    )

    result["actionSuggestions"] = build_action_suggestions(
        content_type=content_type,
        posting_time=posting_time,
        segments=segments,
        risk_dimensions=result["riskDimensions"],
        sensitive_tags=sensitive_tags,
        base_score=result["utilityScore"],
        selected_visibility_plan=selected_visibility_plan,
        visibility_simulation=visibility_simulation,
        risk_dim_boost=copy_risk_dim_boost,
        benefit_multiplier=benefit_multiplier,
        risk_multiplier=risk_multiplier,
    )
    result["meta"]["manualSensitiveTags"] = manual_sensitive_tags
    result["meta"]["autoSensitiveTags"] = auto_sensitive_tags
    result["meta"]["copyText"] = copy_text
    result["meta"]["personalization"] = profile
    if copy_analysis:
        result["meta"]["copyAnalysis"] = copy_analysis

    try:
        history_record = save_analysis_record(payload=payload, result=result)
        result["meta"]["historyRecord"] = history_record
    except Exception as exc:  # pragma: no cover - 不阻断主评估流程
        result["meta"]["historyRecord"] = {"error": str(exc)}

    return result
