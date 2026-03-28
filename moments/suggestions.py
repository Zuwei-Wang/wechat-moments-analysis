from __future__ import annotations

from typing import Any

from .evaluation import evaluate
from .types import AudienceSegment


def build_action_suggestions(
    *,
    content_type: str,
    posting_time: str,
    segments: list[AudienceSegment],
    risk_dimensions: list[dict[str, Any]],
    sensitive_tags: list[str],
    base_score: float,
    selected_visibility_plan: str,
    visibility_simulation: dict[str, Any],
    risk_dim_boost: dict[str, float] | None = None,
    benefit_multiplier: float = 1.0,
    risk_multiplier: float = 1.0,
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    top_dim = risk_dimensions[0]["key"] if risk_dimensions else None

    def _simulate_score(next_posting_time: str, next_tags: list[str], next_segments: list[AudienceSegment]) -> float:
        return evaluate(
            content_type,
            next_posting_time,
            next_tags,
            next_segments,
            risk_dim_boost=risk_dim_boost,
            benefit_multiplier=benefit_multiplier,
            risk_multiplier=risk_multiplier,
        )["utilityScore"]

    def _with_delta(item: dict[str, Any], simulated_score: float | None) -> dict[str, Any]:
        delta = 0.0 if simulated_score is None else round(max(0.0, simulated_score - base_score), 1)
        return {**item, "estimatedDeltaScore": delta}

    if top_dim == "privacy":
        sim_score = _simulate_score(
            posting_time,
            [tag for tag in sensitive_tags if tag not in {"location", "children", "work_confidential", "health"}],
            segments,
        )
        suggestions.append(
            _with_delta(
                {
                    "title": "优先降隐私风险",
                    "detail": "减少定位、孩子信息、工作细节等可识别信息，先发低隐私版本。",
                    "action": {"type": "remove_sensitive_tags", "tags": ["location", "children", "work_confidential", "health"]},
                },
                sim_score,
            )
        )
    elif top_dim == "relationship":
        sim_score = _simulate_score(
            posting_time,
            [tag for tag in sensitive_tags if tag not in {"relationship", "luxury", "complaint", "family_conflict"}],
            segments,
        )
        suggestions.append(
            _with_delta(
                {
                    "title": "优先降关系风险",
                    "detail": "减少可能触发比较或误会的表达，避免直接对比、暗示和点名语气。",
                    "action": {"type": "remove_sensitive_tags", "tags": ["relationship", "luxury", "complaint", "family_conflict"]},
                },
                sim_score,
            )
        )
    elif top_dim == "misunderstanding":
        sim_score = _simulate_score(
            posting_time,
            [tag for tag in sensitive_tags if tag not in {"emotion", "politics", "appearance", "complaint"}],
            segments,
        )
        suggestions.append(
            _with_delta(
                {
                    "title": "优先降误解风险",
                    "detail": "补充上下文，减少情绪化和模糊表达，文案先让不熟的人也能读懂。",
                    "action": {"type": "remove_sensitive_tags", "tags": ["emotion", "politics", "appearance", "complaint"]},
                },
                sim_score,
            )
        )

    if any(tag in sensitive_tags for tag in ("location", "children", "work_confidential")):
        sim_score = _simulate_score(
            posting_time,
            [tag for tag in sensitive_tags if tag not in {"location", "children", "work_confidential"}],
            segments,
        )
        suggestions.append(
            _with_delta(
                {
                    "title": "敏感字段建议降维",
                    "detail": "可先去掉定位/孩子信息/工作细节，再重新评估，通常会显著降低隐私风险。",
                    "action": {"type": "remove_sensitive_tags", "tags": ["location", "children", "work_confidential"]},
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
                    "action": {"type": "set_posting_time", "postingTime": "daytime"},
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
                "action": {"type": "set_visibility_plan", "plan": best["key"]},
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "title": "当前风险结构较平衡",
                "detail": "可保持当前设置发布；若想更稳妥，可再缩小可见范围。",
                "estimatedDeltaScore": 0.0,
                "action": {"type": "noop"},
            }
        )

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in suggestions:
        if item["title"] in seen:
            continue
        if item.get("action", {}).get("type") == "set_visibility_plan" and item["action"].get("plan") == selected_visibility_plan:
            item["estimatedDeltaScore"] = 0.0
        unique.append(item)
        seen.add(item["title"])

    return unique[:4]
