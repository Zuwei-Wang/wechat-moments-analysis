from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from moments import ValidationError, evaluate_request
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


if __name__ == "__main__":
    app.run(debug=True)
