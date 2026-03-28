import unittest

from moments.evaluation import build_score_explanation, evaluate, merge_risk_dimension_boost
from moments.types import AudienceSegment
from moments.visibility import segments_by_visibility_plan


def _sample_segments() -> list[AudienceSegment]:
    return [
        AudienceSegment(
            name="家人",
            ratio=0.4,
            audience_type="family",
            complexity="medium",
            in_group=True,
        ),
        AudienceSegment(
            name="同事",
            ratio=0.6,
            audience_type="classmate_colleague",
            complexity="high",
            in_group=False,
        ),
    ]


class EvaluationTests(unittest.TestCase):
    def test_evaluate_returns_sorted_dimensions(self) -> None:
        result = evaluate(
            content_type="achievement",
            posting_time="late_night",
            sensitive_tags=["money", "location"],
            segments=_sample_segments(),
            risk_dim_boost={"privacy": 0.1},
        )

        values = [item["value"] for item in result["riskDimensions"]]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertGreaterEqual(result["utilityScore"], 0.0)
        self.assertLessEqual(result["utilityScore"], 100.0)
        self.assertGreaterEqual(
            result["topRiskContributors"][0]["risk"],
            result["topRiskContributors"][-1]["risk"],
        )

    def test_merge_risk_dimension_boost_ignores_negative_values(self) -> None:
        merged = merge_risk_dimension_boost(
            {"misunderstanding": 0.1, "relationship": 0.2, "privacy": 0.3},
            {"misunderstanding": -1.0, "relationship": 0.4, "privacy": "0.2"},
        )
        self.assertEqual(merged["misunderstanding"], 0.1)
        self.assertAlmostEqual(merged["relationship"], 0.6)
        self.assertAlmostEqual(merged["privacy"], 0.5)

    def test_build_score_explanation_contains_key_negative_factors(self) -> None:
        all_segments = _sample_segments()
        active_segments = segments_by_visibility_plan("group_only", all_segments, blocked_names=[])
        details = evaluate(
            content_type="achievement",
            posting_time="late_night",
            sensitive_tags=["money", "location"],
            segments=active_segments,
        )["details"]

        explanation = build_score_explanation(
            content_type="achievement",
            posting_time="late_night",
            sensitive_tags=["money", "location"],
            all_segments=all_segments,
            active_segments=active_segments,
            selected_visibility_plan="group_only",
            details=details,
        )

        factors = explanation["loweringFactors"]
        factor_types = {item["type"] for item in factors}
        self.assertIn("posting_time", factor_types)
        for factor in factors:
            self.assertGreaterEqual(factor["share"], 0.0)


if __name__ == "__main__":
    unittest.main()
