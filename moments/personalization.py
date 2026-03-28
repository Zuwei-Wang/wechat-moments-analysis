from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.getenv("MOMENTS_HISTORY_DB", "data/moments_history.db")
DEFAULT_USER_ID = "default"


def _ensure_db_dir() -> None:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_personalization_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS personalization_profile (
                user_id TEXT PRIMARY KEY,
                benefit_multiplier REAL NOT NULL DEFAULT 1.0,
                risk_multiplier REAL NOT NULL DEFAULT 1.0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS personalization_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def get_profile(user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    init_personalization_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as conn:
        row = conn.execute(
            "SELECT user_id, benefit_multiplier, risk_multiplier, updated_at FROM personalization_profile WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            conn.execute(
                """
                INSERT INTO personalization_profile (user_id, benefit_multiplier, risk_multiplier, updated_at)
                VALUES (?, 1.0, 1.0, ?)
                """,
                (user_id, now),
            )
            row = conn.execute(
                "SELECT user_id, benefit_multiplier, risk_multiplier, updated_at FROM personalization_profile WHERE user_id = ?",
                (user_id,),
            ).fetchone()

    return {
        "userId": str(row["user_id"]),
        "benefitMultiplier": round(float(row["benefit_multiplier"]), 4),
        "riskMultiplier": round(float(row["risk_multiplier"]), 4),
        "updatedAt": str(row["updated_at"]),
    }


def apply_feedback(
    *,
    feedback_type: str,
    note: str = "",
    user_id: str = DEFAULT_USER_ID,
) -> dict[str, Any]:
    profile = get_profile(user_id)
    benefit = float(profile["benefitMultiplier"])
    risk = float(profile["riskMultiplier"])

    # 用户认为模型偏保守 -> 降低风险权重并略提收益权重
    if feedback_type == "too_conservative":
        benefit += 0.02
        risk -= 0.03
    # 用户认为模型偏乐观 -> 提高风险权重并略降收益权重
    elif feedback_type == "too_optimistic":
        benefit -= 0.02
        risk += 0.03
    # 评价准确 -> 轻微回归到 1.0，避免长期漂移
    elif feedback_type == "accurate":
        benefit += (1.0 - benefit) * 0.15
        risk += (1.0 - risk) * 0.15
    else:
        raise ValueError("未知反馈类型")

    benefit = round(_clamp(benefit, 0.75, 1.25), 4)
    risk = round(_clamp(risk, 0.75, 1.3), 4)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with _connect() as conn:
        conn.execute(
            """
            UPDATE personalization_profile
            SET benefit_multiplier = ?, risk_multiplier = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (benefit, risk, now, user_id),
        )
        conn.execute(
            """
            INSERT INTO personalization_feedback (user_id, feedback_type, note, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, feedback_type, note[:300], now),
        )

    return {
        "userId": user_id,
        "benefitMultiplier": benefit,
        "riskMultiplier": risk,
        "updatedAt": now,
    }
