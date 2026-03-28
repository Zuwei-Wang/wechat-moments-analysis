from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from moments import ValidationError, apply_feedback, clear_history_records, evaluate_request, get_history_dashboard, get_profile
from moments.constants import (
    AUDIENCE_TYPE_PROFILE,
    COMPLEXITY_MAP,
    CONTENT_BASELINE,
    POSTING_TIME_FACTOR,
    SENSITIVE_RISK_FACTOR,
)

app = Flask(__name__)


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
        result = evaluate_request(payload)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.route("/api/history", methods=["GET"])
def history_api():
    limit_text = request.args.get("limit", "20")
    try:
        limit = int(limit_text)
    except ValueError:
        return jsonify({"error": "limit 必须为整数"}), 400
    data = get_history_dashboard(limit=limit)
    return jsonify(data)


@app.route("/api/history/clear", methods=["POST"])
def history_clear_api():
    result = clear_history_records()
    return jsonify({"ok": True, **result})


@app.route("/api/personalization-profile", methods=["GET"])
def personalization_profile_api():
    return jsonify(get_profile())


@app.route("/api/feedback", methods=["POST"])
def feedback_api():
    payload = request.get_json(silent=True) or {}
    feedback_type = str(payload.get("feedbackType", "")).strip()
    note = str(payload.get("note", "")).strip()
    if not feedback_type:
        return jsonify({"error": "feedbackType 不能为空"}), 400
    try:
        profile = apply_feedback(feedback_type=feedback_type, note=note)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "profile": profile})


if __name__ == "__main__":
    app.run(debug=True)
