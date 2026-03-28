from __future__ import annotations

from typing import Any

from .evaluation import evaluate
from .types import AudienceSegment


def clone_segment(segment: AudienceSegment) -> AudienceSegment:
    return AudienceSegment(
        name=segment.name,
        ratio=segment.ratio,
        audience_type=segment.audience_type,
        complexity=segment.complexity,
        in_group=segment.in_group,
    )


def segments_by_visibility_plan(
    plan: str,
    segments: list[AudienceSegment],
    blocked_names: list[str],
) -> list[AudienceSegment]:
    blocked_set = {name.strip() for name in blocked_names if name.strip()}
    if plan == "group_only":
        return [clone_segment(s) for s in segments if s.in_group]
    if plan == "hide_selected":
        return [clone_segment(s) for s in segments if s.name not in blocked_set]
    return [clone_segment(s) for s in segments]


def visibility_plan_label(plan: str) -> str:
    return {
        "all_visible": "全部可见",
        "group_only": "仅分组可见",
        "hide_selected": "屏蔽指定人群",
    }.get(plan, "全部可见")


def simulate_visibility(
    content_type: str,
    posting_time: str,
    sensitive_tags: list[str],
    segments: list[AudienceSegment],
    blocked_names: list[str],
    risk_dim_boost: dict[str, float] | None = None,
) -> dict[str, Any]:
    blocked_set = {name.strip() for name in blocked_names if name.strip()}
    scenario_defs: list[tuple[str, str, list[AudienceSegment]]] = [
        ("all_visible", "全部可见", [clone_segment(s) for s in segments]),
        ("group_only", "仅分组可见", [clone_segment(s) for s in segments if s.in_group]),
        (
            "hide_selected",
            "屏蔽指定人群",
            [clone_segment(s) for s in segments if s.name not in blocked_set],
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

        result = evaluate(
            content_type,
            posting_time,
            sensitive_tags,
            scenario_segments,
            risk_dim_boost=risk_dim_boost,
        )
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
