from __future__ import annotations

from typing import Any

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

AUDIENCE_TYPE_PROFILE: dict[str, dict[str, Any]] = {
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

VISIBILITY_PLANS: set[str] = {"all_visible", "group_only", "hide_selected"}
