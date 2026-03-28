from __future__ import annotations

import math
from typing import Any

from .constants import (
    AUDIENCE_TYPE_PROFILE,
    CONTENT_BASELINE,
    POSTING_TIME_FACTOR,
    RISK_DIMENSION_KEYS,
    RISK_DIMENSION_LABELS,
    SENSITIVE_RISK_DIM_FACTOR,
)
from .types import AudienceSegment


def utility_to_percent_score(utility: float) -> float:
    return round(100 / (1 + math.exp(-2.4 * utility)), 1)


def make_suggestion(utility: float) -> tuple[str, str]:
    score = utility_to_percent_score(utility)
    if score >= 65:
        return "建议发布", "safe"
    if score >= 45:
        return "谨慎发布", "warning"
    return "不建议发布", "danger"


def build_sensitivity_risk_by_dimension(sensitive_tags: list[str]) -> dict[str, float]:
    sensitivity_risk_by_dim = {dim: 0.0 for dim in RISK_DIMENSION_KEYS}
    for tag in sensitive_tags:
        dim_map = SENSITIVE_RISK_DIM_FACTOR[tag]
        for dim in RISK_DIMENSION_KEYS:
            sensitivity_risk_by_dim[dim] += dim_map[dim]
    return sensitivity_risk_by_dim


def merge_risk_dimension_boost(
    sensitivity_risk_by_dim: dict[str, float],
    risk_dim_boost: dict[str, float] | None,
) -> dict[str, float]:
    if not risk_dim_boost:
        return sensitivity_risk_by_dim
    merged = dict(sensitivity_risk_by_dim)
    for dim in RISK_DIMENSION_KEYS:
        merged[dim] = merged.get(dim, 0.0) + max(0.0, float(risk_dim_boost.get(dim, 0.0)))
    return merged


def evaluate(
    content_type: str,
    posting_time: str,
    sensitive_tags: list[str],
    segments: list[AudienceSegment],
    risk_dim_boost: dict[str, float] | None = None,
) -> dict[str, Any]:
    baseline = CONTENT_BASELINE[content_type]
    time_factor = POSTING_TIME_FACTOR[posting_time]
    sensitivity_risk_by_dim = build_sensitivity_risk_by_dimension(sensitive_tags)
    sensitivity_risk_by_dim = merge_risk_dimension_boost(sensitivity_risk_by_dim, risk_dim_boost)
    sensitivity_risk = sum(sensitivity_risk_by_dim.values())

    total_ratio = sum(segment.ratio for segment in segments)
    utility = 0.0
    risk_dimension_totals = {dim: 0.0 for dim in RISK_DIMENSION_KEYS}
    risk_contributions: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []

    for segment in segments:
        p_i = segment.ratio / total_ratio
        profile = AUDIENCE_TYPE_PROFILE[segment.audience_type]
        effective_benefit = profile["benefit"] * (1 + baseline["benefit"]) * time_factor["benefit"]

        risk_breakdown_raw: dict[str, float] = {}
        for dim in RISK_DIMENSION_KEYS:
            base_dim_cost = profile["cost"] * profile["risk_dim"][dim]
            effective_dim_cost = (
                base_dim_cost
                * (1 + baseline["risk"] + sensitivity_risk_by_dim[dim])
                * time_factor["risk"]
            )
            dim_risk = p_i * effective_dim_cost * segment.complexity_factor
            risk_breakdown_raw[dim] = dim_risk
            risk_dimension_totals[dim] += dim_risk

        risk = sum(risk_breakdown_raw.values())
        gain = p_i * effective_benefit
        utility_piece = gain - risk
        utility += utility_piece

        detail_rows.append(
            {
                "name": segment.name,
                "audienceType": segment.audience_type,
                "baseBenefit": round(profile["benefit"], 4),
                "baseRisk": round(profile["cost"], 4),
                "weight": round(p_i, 4),
                "gain": round(gain, 4),
                "risk": round(risk, 4),
                "riskBreakdown": {dim: round(risk_breakdown_raw[dim], 4) for dim in RISK_DIMENSION_KEYS},
                "utility": round(utility_piece, 4),
            }
        )
        risk_contributions.append({"name": segment.name, "risk": risk})

    risk_contributions.sort(key=lambda item: item["risk"], reverse=True)
    top_risk = [{"name": item["name"], "risk": round(item["risk"], 4)} for item in risk_contributions[:3]]

    total_risk_value = sum(risk_dimension_totals.values())
    risk_dimensions = [
        {
            "key": dim,
            "label": RISK_DIMENSION_LABELS[dim],
            "value": round(risk_dimension_totals[dim], 4),
            "share": round(risk_dimension_totals[dim] / total_risk_value, 4) if total_risk_value > 0 else 0.0,
        }
        for dim in RISK_DIMENSION_KEYS
    ]
    risk_dimensions.sort(key=lambda item: item["value"], reverse=True)

    suggestion, level = make_suggestion(utility)

    return {
        "utilityScore": utility_to_percent_score(utility),
        "utilityRaw": round(utility, 4),
        "suggestion": suggestion,
        "level": level,
        "topRiskContributors": top_risk,
        "riskDimensions": risk_dimensions,
        "details": detail_rows,
        "meta": {
            "contentType": content_type,
            "postingTime": posting_time,
            "sensitiveTags": sensitive_tags,
            "sensitivityRisk": round(sensitivity_risk, 4),
            "sensitivityRiskByDimension": {dim: round(sensitivity_risk_by_dim[dim], 4) for dim in RISK_DIMENSION_KEYS},
            "copyRiskBoostByDimension": {
                dim: round(float((risk_dim_boost or {}).get(dim, 0.0)), 4) for dim in RISK_DIMENSION_KEYS
            },
            "timeBenefitFactor": time_factor["benefit"],
            "timeRiskFactor": time_factor["risk"],
        },
    }


def build_score_explanation(
    *,
    content_type: str,
    posting_time: str,
    sensitive_tags: list[str],
    all_segments: list[AudienceSegment],
    active_segments: list[AudienceSegment],
    selected_visibility_plan: str,
    details: list[dict[str, Any]],
    risk_dim_boost: dict[str, float] | None = None,
) -> dict[str, Any]:
    baseline = CONTENT_BASELINE[content_type]
    time_factor = POSTING_TIME_FACTOR[posting_time]
    sensitivity_risk_by_dim = build_sensitivity_risk_by_dimension(sensitive_tags)
    sensitivity_risk_by_dim = merge_risk_dimension_boost(sensitivity_risk_by_dim, risk_dim_boost)
    total_ratio = sum(s.ratio for s in active_segments)
    if total_ratio <= 0:
        return {"loweringFactors": []}

    factors: list[dict[str, Any]] = []

    for row in details:
        impact = float(row.get("risk", 0))
        if impact <= 0:
            continue
        factors.append(
            {
                "name": f"{row['name']}人群风险",
                "impact": impact,
                "type": "audience_risk",
                "direction": "negative",
                "detail": "该人群带来的综合风险贡献较高。",
            }
        )

    for tag in sensitive_tags:
        tag_impact = 0.0
        for segment in active_segments:
            p_i = segment.ratio / total_ratio
            profile = AUDIENCE_TYPE_PROFILE[segment.audience_type]
            for dim in RISK_DIMENSION_KEYS:
                base_dim_cost = profile["cost"] * profile["risk_dim"][dim]
                tag_impact += (
                    p_i
                    * base_dim_cost
                    * time_factor["risk"]
                    * segment.complexity_factor
                    * SENSITIVE_RISK_DIM_FACTOR[tag][dim]
                )
        if tag_impact <= 0:
            continue
        factors.append(
            {
                "name": f"敏感信息：{tag}",
                "impact": round(tag_impact, 4),
                "type": "sensitive_tag",
                "direction": "negative",
                "detail": "该敏感标签会放大风险系数，拉低综合得分。",
            }
        )

    for segment in active_segments:
        if segment.complexity_factor <= 1:
            continue
        p_i = segment.ratio / total_ratio
        profile = AUDIENCE_TYPE_PROFILE[segment.audience_type]
        base_cost = 0.0
        for dim in RISK_DIMENSION_KEYS:
            base_dim_cost = profile["cost"] * profile["risk_dim"][dim]
            base_cost += base_dim_cost * (1 + baseline["risk"] + sensitivity_risk_by_dim[dim])
        complexity_penalty = p_i * base_cost * time_factor["risk"] * (segment.complexity_factor - 1)
        if complexity_penalty <= 0:
            continue
        factors.append(
            {
                "name": f"{segment.name}关系复杂度惩罚",
                "impact": round(complexity_penalty, 4),
                "type": "complexity_penalty",
                "direction": "negative",
                "detail": "关系敏感度较高会放大该人群风险。",
            }
        )

    if posting_time != "daytime":
        curr = evaluate(
            content_type,
            posting_time,
            sensitive_tags,
            active_segments,
            risk_dim_boost=risk_dim_boost,
        )["utilityRaw"]
        day = evaluate(
            content_type,
            "daytime",
            sensitive_tags,
            active_segments,
            risk_dim_boost=risk_dim_boost,
        )["utilityRaw"]
        penalty = max(0.0, day - curr)
        if penalty > 0:
            factors.append(
                {
                    "name": "发布时间惩罚",
                    "impact": round(penalty, 4),
                    "type": "posting_time",
                    "direction": "negative",
                    "detail": "当前发布时间相对白天会增加风险或降低收益。",
                }
            )

    if selected_visibility_plan != "all_visible":
        all_visible_score = evaluate(
            content_type,
            posting_time,
            sensitive_tags,
            all_segments,
            risk_dim_boost=risk_dim_boost,
        )["utilityRaw"]
        selected_score = evaluate(
            content_type,
            posting_time,
            sensitive_tags,
            active_segments,
            risk_dim_boost=risk_dim_boost,
        )["utilityRaw"]
        penalty = max(0.0, all_visible_score - selected_score)
        if penalty > 0:
            factors.append(
                {
                    "name": "可见方案折损",
                    "impact": round(penalty, 4),
                    "type": "visibility_tradeoff",
                    "direction": "negative",
                    "detail": "当前可见方案相较全部可见带来额外分数损失。",
                }
            )

    negative_factors = [f for f in factors if f["direction"] == "negative" and f["impact"] > 0]
    negative_factors.sort(key=lambda item: item["impact"], reverse=True)
    top = negative_factors[:6]
    total_impact = sum(item["impact"] for item in top)
    for item in top:
        item["share"] = round((item["impact"] / total_impact) * 100, 1) if total_impact > 0 else 0.0

    return {"loweringFactors": top, "totalImpact": round(total_impact, 4)}
