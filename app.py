from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from flask import Flask, jsonify, render_template, request


app = Flask(__name__)

CONTENT_BASELINE: dict[str, dict[str, float]] = {
    "daily": {"benefit": 0.45, "risk": 0.25},
    "achievement": {"benefit": 0.75, "risk": 0.55},
    "emotion": {"benefit": 0.55, "risk": 0.6},
    "travel": {"benefit": 0.6, "risk": 0.4},
    "fitness": {"benefit": 0.58, "risk": 0.38},
}

COMPLEXITY_MAP: dict[str, float] = {
    "low": 0.8,
    "medium": 1.0,
    "high": 1.3,
}

SENSITIVE_RISK_FACTOR: dict[str, float] = {
    "money": 0.18,
    "emotion": 0.16,
    "relationship": 0.2,
    "location": 0.12,
    "politics": 0.24,
    "work_confidential": 0.26,
    "health": 0.15,
    "family_conflict": 0.2,
    "children": 0.17,
    "appearance": 0.14,
    "luxury": 0.19,
    "complaint": 0.18,
}

RISK_DIMENSION_KEYS: tuple[str, str, str] = (
    "misunderstanding",
    "relationship",
    "privacy",
)

RISK_DIMENSION_LABELS: dict[str, str] = {
    "misunderstanding": "误解风险",
    "relationship": "关系风险",
    "privacy": "隐私风险",
}

SENSITIVE_RISK_DIM_FACTOR: dict[str, dict[str, float]] = {
    "money": {"misunderstanding": 0.05, "relationship": 0.08, "privacy": 0.05},
    "emotion": {"misunderstanding": 0.08, "relationship": 0.05, "privacy": 0.03},
    "relationship": {"misunderstanding": 0.06, "relationship": 0.1, "privacy": 0.04},
    "location": {"misunderstanding": 0.02, "relationship": 0.03, "privacy": 0.07},
    "politics": {"misunderstanding": 0.14, "relationship": 0.08, "privacy": 0.02},
    "work_confidential": {"misunderstanding": 0.05, "relationship": 0.03, "privacy": 0.18},
    "health": {"misunderstanding": 0.05, "relationship": 0.03, "privacy": 0.07},
    "family_conflict": {"misunderstanding": 0.06, "relationship": 0.1, "privacy": 0.04},
    "children": {"misunderstanding": 0.03, "relationship": 0.04, "privacy": 0.1},
    "appearance": {"misunderstanding": 0.08, "relationship": 0.04, "privacy": 0.02},
    "luxury": {"misunderstanding": 0.05, "relationship": 0.11, "privacy": 0.03},
    "complaint": {"misunderstanding": 0.08, "relationship": 0.08, "privacy": 0.02},
}

AUDIENCE_TYPE_PROFILE: dict[str, dict[str, float]] = {
    "family": {
        "benefit": 0.52,
        "cost": 0.24,
        "risk_dim": {"misunderstanding": 0.3, "relationship": 0.45, "privacy": 0.25},
    },
    "close_friend": {
        "benefit": 0.78,
        "cost": 0.3,
        "risk_dim": {"misunderstanding": 0.28, "relationship": 0.44, "privacy": 0.28},
    },
    "classmate_colleague": {
        "benefit": 0.58,
        "cost": 0.48,
        "risk_dim": {"misunderstanding": 0.42, "relationship": 0.38, "privacy": 0.2},
    },
    "acquaintance": {
        "benefit": 0.32,
        "cost": 0.68,
        "risk_dim": {"misunderstanding": 0.35, "relationship": 0.3, "privacy": 0.35},
    },
    "special": {
        "benefit": 0.45,
        "cost": 0.72,
        "risk_dim": {"misunderstanding": 0.32, "relationship": 0.5, "privacy": 0.18},
    },
}

POSTING_TIME_FACTOR: dict[str, dict[str, float]] = {
    "morning": {"benefit": 1.05, "risk": 0.95},
    "daytime": {"benefit": 1.0, "risk": 1.0},
    "evening": {"benefit": 1.08, "risk": 1.05},
    "late_night": {"benefit": 0.92, "risk": 1.2},
}


@dataclass
class AudienceSegment:
    name: str
    ratio: float
    audience_type: str
    complexity: str
    in_group: bool

    @property
    def complexity_factor(self) -> float:
        return COMPLEXITY_MAP.get(self.complexity, 1.0)


class ValidationError(Exception):
    pass


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
) -> tuple[str, str, list[str], list[AudienceSegment], list[str]]:
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

    return content_type, posting_time, sensitive_tags, segments, blocked_names


def _make_suggestion(utility: float) -> tuple[str, str]:
    score = _utility_to_percent_score(utility)
    if score >= 65:
        return "建议发布", "safe"
    if score >= 45:
        return "谨慎发布", "warning"
    return "不建议发布", "danger"


def _utility_to_percent_score(utility: float) -> float:
    # Logistic mapping to normalize unbounded utility into a stable 0-100 score.
    return round(100 / (1 + math.exp(-2.4 * utility)), 1)


def evaluate(
    content_type: str, posting_time: str, sensitive_tags: list[str], segments: list[AudienceSegment]
) -> dict[str, Any]:
    baseline = CONTENT_BASELINE[content_type]
    time_factor = POSTING_TIME_FACTOR[posting_time]
    sensitivity_risk_by_dim = {dim: 0.0 for dim in RISK_DIMENSION_KEYS}
    for tag in sensitive_tags:
        dim_map = SENSITIVE_RISK_DIM_FACTOR[tag]
        for dim in RISK_DIMENSION_KEYS:
            sensitivity_risk_by_dim[dim] += dim_map[dim]

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
    top_risk = [
        {"name": item["name"], "risk": round(item["risk"], 4)}
        for item in risk_contributions[:3]
    ]
    total_risk_value = sum(risk_dimension_totals.values())
    risk_dimensions = [
        {
            "key": dim,
            "label": RISK_DIMENSION_LABELS[dim],
            "value": round(risk_dimension_totals[dim], 4),
            "share": round(
                risk_dimension_totals[dim] / total_risk_value, 4
            )
            if total_risk_value > 0
            else 0.0,
        }
        for dim in RISK_DIMENSION_KEYS
    ]
    risk_dimensions.sort(key=lambda item: item["value"], reverse=True)

    suggestion, level = _make_suggestion(utility)

    percent_score = _utility_to_percent_score(utility)

    return {
        "utilityScore": percent_score,
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
            "sensitivityRiskByDimension": {
                dim: round(sensitivity_risk_by_dim[dim], 4) for dim in RISK_DIMENSION_KEYS
            },
            "timeBenefitFactor": time_factor["benefit"],
            "timeRiskFactor": time_factor["risk"],
        },
    }


def _clone_segment(segment: AudienceSegment) -> AudienceSegment:
    return AudienceSegment(
        name=segment.name,
        ratio=segment.ratio,
        audience_type=segment.audience_type,
        complexity=segment.complexity,
        in_group=segment.in_group,
    )


def _simulate_visibility(
    content_type: str,
    posting_time: str,
    sensitive_tags: list[str],
    segments: list[AudienceSegment],
    blocked_names: list[str],
) -> dict[str, Any]:
    blocked_set = {name.strip() for name in blocked_names if name.strip()}

    scenario_defs: list[tuple[str, str, list[AudienceSegment]]] = [
        ("all_visible", "全部可见", [_clone_segment(s) for s in segments]),
        ("group_only", "仅分组可见", [_clone_segment(s) for s in segments if s.in_group]),
        (
            "hide_selected",
            "屏蔽指定人群",
            [_clone_segment(s) for s in segments if s.name not in blocked_set],
        ),
    ]

    scenario_results: list[dict[str, Any]] = []
    for key, label, scenario_segments in scenario_defs:
        if not scenario_segments:
            scenario_results.append(
                {
                    "key": key,
                    "label": label,
                    "available": False,
                    "reason": "该方案下没有可见受众，无法计算",
                }
            )
            continue

        result = evaluate(content_type, posting_time, sensitive_tags, scenario_segments)
        scenario_results.append(
                {
                    "key": key,
                    "label": label,
                    "available": True,
                    "utilityScore": result["utilityScore"],
                    "utilityRaw": result["utilityRaw"],
                    "suggestion": result["suggestion"],
                    "level": result["level"],
                }
            )

    available = [item for item in scenario_results if item["available"]]
    best = max(available, key=lambda item: item["utilityScore"]) if available else None
    return {
        "blockedAudienceNames": sorted(blocked_set),
        "scenarios": scenario_results,
        "bestScenario": best,
    }


def _build_action_suggestions(
    *,
    content_type: str,
    posting_time: str,
    segments: list[AudienceSegment],
    risk_dimensions: list[dict[str, Any]],
    sensitive_tags: list[str],
    base_score: float,
    visibility_simulation: dict[str, Any],
 ) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []

    top_dim = risk_dimensions[0]["key"] if risk_dimensions else None

    def _simulate_score(next_posting_time: str, next_tags: list[str], next_segments: list[AudienceSegment]) -> float:
        return evaluate(content_type, next_posting_time, next_tags, next_segments)["utilityScore"]

    def _with_delta(item: dict[str, str], simulated_score: float | None) -> dict[str, Any]:
        delta = 0.0 if simulated_score is None else round(max(0.0, simulated_score - base_score), 1)
        return {**item, "estimatedDeltaScore": delta}

    if top_dim == "privacy":
        stripped_tags = [tag for tag in sensitive_tags if tag not in {"location", "children", "work_confidential", "health"}]
        sim_score = _simulate_score(posting_time, stripped_tags, segments)
        suggestions.append(
            _with_delta(
            {
                "title": "优先降隐私风险",
                "detail": "减少定位、孩子信息、工作细节等可识别信息，先发低隐私版本。",
            },
            sim_score,
            )
        )
    elif top_dim == "relationship":
        stripped_tags = [tag for tag in sensitive_tags if tag not in {"relationship", "luxury", "complaint", "family_conflict"}]
        sim_score = _simulate_score(posting_time, stripped_tags, segments)
        suggestions.append(
            _with_delta(
            {
                "title": "优先降关系风险",
                "detail": "减少可能触发比较或误会的表达，避免直接对比、暗示和点名语气。",
            },
            sim_score,
            )
        )
    elif top_dim == "misunderstanding":
        stripped_tags = [tag for tag in sensitive_tags if tag not in {"emotion", "politics", "appearance", "complaint"}]
        sim_score = _simulate_score(posting_time, stripped_tags, segments)
        suggestions.append(
            _with_delta(
            {
                "title": "优先降误解风险",
                "detail": "补充上下文，减少情绪化和模糊表达，文案先让不熟的人也能读懂。",
            },
            sim_score,
            )
        )

    if any(tag in sensitive_tags for tag in ("location", "children", "work_confidential")):
        stripped_tags = [tag for tag in sensitive_tags if tag not in {"location", "children", "work_confidential"}]
        sim_score = _simulate_score(posting_time, stripped_tags, segments)
        suggestions.append(
            _with_delta(
            {
                "title": "敏感字段建议降维",
                "detail": "可先去掉定位/孩子信息/工作细节，再重新评估，通常会显著降低隐私风险。",
            },
            sim_score,
            )
        )

    if posting_time == "late_night":
        sim_score = _simulate_score("daytime", sensitive_tags, segments)
        suggestions.append(
            _with_delta(
            {
                "title": "建议调整发布时间",
                "detail": "深夜发布通常放大风险，建议改到白天或早晨后再发。",
            },
            sim_score,
            )
        )

    best = visibility_simulation.get("bestScenario")
    if best and best.get("key") != "all_visible":
        suggestions.append(
            {
                "title": "建议优化可见范围",
                "detail": f"当前最优方案是“{best['label']}”，建议先按该方案发布。",
                "estimatedDeltaScore": round(max(0.0, best.get("utilityScore", base_score) - base_score), 1),
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "title": "当前风险结构较平衡",
                "detail": "可保持当前设置发布；若想更稳妥，可再缩小可见范围。",
                "estimatedDeltaScore": 0.0,
            }
        )

    # Deduplicate by title while preserving order.
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in suggestions:
        if item["title"] in seen:
            continue
        unique.append(item)
        seen.add(item["title"])

    return unique[:4]


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/start-analysis")
def start_analysis() -> str:
    return render_template(
        "start_analysis.html",
        content_types=CONTENT_BASELINE,
        complexity_map=COMPLEXITY_MAP,
        sensitive_tags=SENSITIVE_RISK_FACTOR,
        posting_time_factor=POSTING_TIME_FACTOR,
        audience_type_profile=AUDIENCE_TYPE_PROFILE,
    )


@app.route("/analysis-result")
def analysis_result() -> str:
    return render_template("analysis_result.html")


@app.route("/api/evaluate", methods=["POST"])
def evaluate_api():
    payload = request.get_json(silent=True) or {}

    try:
        content_type, posting_time, sensitive_tags, segments, blocked_names = parse_payload(payload)
        result = evaluate(content_type, posting_time, sensitive_tags, segments)
        visibility_simulation = _simulate_visibility(
            content_type, posting_time, sensitive_tags, segments, blocked_names
        )
        result["visibilitySimulation"] = visibility_simulation
        result["actionSuggestions"] = _build_action_suggestions(
            content_type=content_type,
            posting_time=posting_time,
            segments=segments,
            risk_dimensions=result["riskDimensions"],
            sensitive_tags=sensitive_tags,
            base_score=result["utilityScore"],
            visibility_simulation=visibility_simulation,
        )
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
