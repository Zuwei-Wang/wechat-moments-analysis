import os
import tempfile
import unittest

import moments.history as history
import moments.personalization as personalization
from app import app


def _build_payload() -> dict:
    return {
        "contentType": "achievement",
        "postingTime": "evening",
        "copyText": "今天升职加薪，真的太开心了。",
        "sensitiveTags": ["money"],
        "selectedVisibilityPlan": "all_visible",
        "blockedAudienceNames": ["同事"],
        "audiences": [
            {
                "name": "家人",
                "ratio": 0.4,
                "audienceType": "family",
                "complexity": "low",
                "inGroup": True,
            },
            {
                "name": "同事",
                "ratio": 0.6,
                "audienceType": "classmate_colleague",
                "complexity": "high",
                "inGroup": False,
            },
        ],
    }


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "moments_test.db")
        self.old_history_db_path = history.DB_PATH
        self.old_personalization_db_path = personalization.DB_PATH
        history.DB_PATH = self.db_path
        personalization.DB_PATH = self.db_path

        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self) -> None:
        history.DB_PATH = self.old_history_db_path
        personalization.DB_PATH = self.old_personalization_db_path
        self.temp_dir.cleanup()

    def test_evaluate_api_success_and_history_generated(self) -> None:
        response = self.client.post("/api/evaluate", json=_build_payload())
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn("utilityScore", body)
        self.assertIn("historyRecord", body["meta"])
        self.assertIn("id", body["meta"]["historyRecord"])

        history_response = self.client.get("/api/history?limit=10")
        self.assertEqual(history_response.status_code, 200)
        history_body = history_response.get_json()
        self.assertEqual(history_body["total"], 1)

    def test_evaluate_api_validation_error(self) -> None:
        payload = _build_payload()
        payload["contentType"] = "unknown_type"
        response = self.client.post("/api/evaluate", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_history_api_limit_validation(self) -> None:
        response = self.client.get("/api/history?limit=abc")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

    def test_feedback_and_profile_api(self) -> None:
        invalid_response = self.client.post("/api/feedback", json={"note": "缺少类型"})
        self.assertEqual(invalid_response.status_code, 400)

        response = self.client.post("/api/feedback", json={"feedbackType": "too_conservative", "note": "更激进一点"})
        self.assertEqual(response.status_code, 200)
        profile = response.get_json()["profile"]
        self.assertGreater(profile["benefitMultiplier"], 1.0)
        self.assertLess(profile["riskMultiplier"], 1.0)

        profile_response = self.client.get("/api/personalization-profile")
        self.assertEqual(profile_response.status_code, 200)
        profile_body = profile_response.get_json()
        self.assertEqual(profile_body["benefitMultiplier"], profile["benefitMultiplier"])
        self.assertEqual(profile_body["riskMultiplier"], profile["riskMultiplier"])

    def test_clear_history_api(self) -> None:
        self.client.post("/api/evaluate", json=_build_payload())
        clear_response = self.client.post("/api/history/clear")
        self.assertEqual(clear_response.status_code, 200)
        self.assertTrue(clear_response.get_json()["ok"])

        history_response = self.client.get("/api/history?limit=10")
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.get_json()["total"], 0)


if __name__ == "__main__":
    unittest.main()
