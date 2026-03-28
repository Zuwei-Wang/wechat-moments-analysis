import unittest

from moments.copywriting import analyze_copy_text


class CopywritingAnalysisTests(unittest.TestCase):
    def test_detects_tags_and_dimension_boost(self) -> None:
        result = analyze_copy_text("今天升职加薪太开心了，还顺手发了定位。")

        self.assertIn("money", result["detectedTags"])
        self.assertIn("emotion", result["detectedTags"])
        self.assertIn("location", result["detectedTags"])
        self.assertGreater(result["emotionIntensity"]["score"], 0.0)
        self.assertGreater(result["showoffIntensity"]["score"], 0.0)
        self.assertGreater(result["privacyIntensity"]["score"], 0.0)
        self.assertGreater(result["dimensionBoost"]["privacy"], 0.0)


if __name__ == "__main__":
    unittest.main()
