import unittest

from moments.types import AudienceSegment
from moments.visibility import segments_by_visibility_plan, simulate_visibility


def _segments() -> list[AudienceSegment]:
    return [
        AudienceSegment(
            name="A组同学",
            ratio=0.5,
            audience_type="classmate_colleague",
            complexity="medium",
            in_group=True,
        ),
        AudienceSegment(
            name="B组同学",
            ratio=0.5,
            audience_type="acquaintance",
            complexity="high",
            in_group=False,
        ),
    ]


class VisibilityTests(unittest.TestCase):
    def test_segments_by_visibility_plan_filters_correctly(self) -> None:
        segments = _segments()
        self.assertEqual(len(segments_by_visibility_plan("all_visible", segments, [])), 2)
        self.assertEqual(len(segments_by_visibility_plan("group_only", segments, [])), 1)
        self.assertEqual(len(segments_by_visibility_plan("hide_selected", segments, ["B组同学"])), 1)

    def test_simulate_visibility_handles_unavailable_scenarios(self) -> None:
        segments = [
            AudienceSegment(
                name="仅外部人群",
                ratio=1.0,
                audience_type="acquaintance",
                complexity="medium",
                in_group=False,
            )
        ]
        result = simulate_visibility(
            content_type="daily",
            posting_time="daytime",
            sensitive_tags=[],
            segments=segments,
            blocked_names=["仅外部人群"],
        )
        scenarios = {item["key"]: item for item in result["scenarios"]}
        self.assertTrue(scenarios["all_visible"]["available"])
        self.assertFalse(scenarios["group_only"]["available"])
        self.assertFalse(scenarios["hide_selected"]["available"])
        self.assertEqual(result["bestScenario"]["key"], "all_visible")


if __name__ == "__main__":
    unittest.main()
