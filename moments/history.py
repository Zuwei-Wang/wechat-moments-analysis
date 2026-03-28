from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.getenv("MOMENTS_HISTORY_DB", "data/moments_history.db")


def _ensure_db_dir() -> None:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_history_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                content_type TEXT NOT NULL,
                posting_time TEXT NOT NULL,
                visibility_plan TEXT NOT NULL,
                utility_score REAL NOT NULL,
                utility_raw REAL NOT NULL,
                level TEXT NOT NULL,
                suggestion TEXT NOT NULL,
                sensitive_tags_json TEXT NOT NULL,
                risk_dimensions_json TEXT NOT NULL,
                top_risk_json TEXT NOT NULL,
                copy_analysis_json TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_history_created_at ON analysis_history(created_at DESC)"
        )


def save_analysis_record(
    *,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    init_history_db()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record = {
        "created_at": created_at,
        "content_type": result.get("meta", {}).get("contentType", payload.get("contentType", "unknown")),
        "posting_time": result.get("meta", {}).get("postingTime", payload.get("postingTime", "daytime")),
        "visibility_plan": result.get("meta", {}).get("selectedVisibilityPlan", payload.get("selectedVisibilityPlan", "all_visible")),
        "utility_score": float(result.get("utilityScore", 0.0)),
        "utility_raw": float(result.get("utilityRaw", 0.0)),
        "level": str(result.get("level", "warning")),
        "suggestion": str(result.get("suggestion", "")),
        "sensitive_tags_json": json.dumps(result.get("meta", {}).get("sensitiveTags", []), ensure_ascii=False),
        "risk_dimensions_json": json.dumps(result.get("riskDimensions", []), ensure_ascii=False),
        "top_risk_json": json.dumps(result.get("topRiskContributors", []), ensure_ascii=False),
        "copy_analysis_json": json.dumps(result.get("meta", {}).get("copyAnalysis"), ensure_ascii=False),
    }
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO analysis_history (
                created_at,
                content_type,
                posting_time,
                visibility_plan,
                utility_score,
                utility_raw,
                level,
                suggestion,
                sensitive_tags_json,
                risk_dimensions_json,
                top_risk_json,
                copy_analysis_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["created_at"],
                record["content_type"],
                record["posting_time"],
                record["visibility_plan"],
                record["utility_score"],
                record["utility_raw"],
                record["level"],
                record["suggestion"],
                record["sensitive_tags_json"],
                record["risk_dimensions_json"],
                record["top_risk_json"],
                record["copy_analysis_json"],
            ),
        )
        record_id = int(cur.lastrowid)
    return {"id": record_id, "createdAt": created_at}


def _safe_json_loads(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def get_history_dashboard(limit: int = 20) -> dict[str, Any]:
    init_history_db()
    safe_limit = max(1, min(100, int(limit)))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id, created_at, content_type, posting_time, visibility_plan,
                utility_score, utility_raw, level, suggestion,
                sensitive_tags_json
            FROM analysis_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    records: list[dict[str, Any]] = []
    risk_level_counts = {"safe": 0, "warning": 0, "danger": 0}
    high_risk_tag_counts: dict[str, int] = {}
    score_sum = 0.0

    for row in rows:
        tags = _safe_json_loads(row["sensitive_tags_json"], [])
        level = str(row["level"])
        score = float(row["utility_score"])
        score_sum += score
        if level in risk_level_counts:
            risk_level_counts[level] += 1

        is_high_risk = level == "danger" or score < 45
        if is_high_risk:
            for tag in tags:
                high_risk_tag_counts[tag] = high_risk_tag_counts.get(tag, 0) + 1

        records.append(
            {
                "id": int(row["id"]),
                "createdAt": row["created_at"],
                "contentType": row["content_type"],
                "postingTime": row["posting_time"],
                "visibilityPlan": row["visibility_plan"],
                "utilityScore": round(score, 1),
                "utilityRaw": round(float(row["utility_raw"]), 4),
                "level": level,
                "suggestion": row["suggestion"],
                "sensitiveTags": tags,
            }
        )

    records_for_trend = list(reversed(records))
    trend = [{"x": idx + 1, "score": item["utilityScore"], "level": item["level"]} for idx, item in enumerate(records_for_trend)]
    top_high_risk_tags = sorted(high_risk_tag_counts.items(), key=lambda item: item[1], reverse=True)[:8]
    avg_score = round(score_sum / len(records), 1) if records else 0.0

    return {
        "limit": safe_limit,
        "total": len(records),
        "avgScore": avg_score,
        "riskLevelCounts": risk_level_counts,
        "trend": trend,
        "highRiskTags": [{"tag": tag, "count": count} for tag, count in top_high_risk_tags],
        "recentRecords": records,
    }


def clear_history_records() -> dict[str, int]:
    init_history_db()
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(1) AS cnt FROM analysis_history").fetchone()
        deleted = int(row["cnt"]) if row else 0
        conn.execute("DELETE FROM analysis_history")
    return {"deleted": deleted}
