import unittest

from app.services.ai_grading_service import AIGradingService


class AIGradingServiceRubricCoverageTests(unittest.TestCase):
    def test_enforce_rubric_coverage_adds_missing_criteria_and_recomputes_score(self) -> None:
        response = {
            "normalized_score_10": 9.5,
            "status": "AC",
            "criteria_scores": [
                {
                    "criterion": "Đúng thuật toán",
                    "earned": 3,
                    "max": 6,
                    "feedback": "Đạt phần cốt lõi",
                    "evidence": "Có dùng DFS",
                }
            ],
        }
        rubric_context = {
            "criteria": [
                {"name": "Đúng thuật toán", "max_score": 6},
                {"name": "Xử lý biên", "max_score": 4},
            ]
        }

        updated = AIGradingService._enforce_rubric_coverage(response, rubric_context)

        self.assertEqual(updated["status"], "WA")
        self.assertEqual(updated["normalized_score_10"], 3.0)
        self.assertEqual(len(updated["criteria_scores"]), 2)
        self.assertEqual(updated["criteria_scores"][0]["criterion"], "Đúng thuật toán")
        self.assertEqual(updated["criteria_scores"][1]["criterion"], "Xử lý biên")
        self.assertEqual(updated["criteria_scores"][1]["earned"], 0.0)
        self.assertEqual(updated["criteria_scores"][1]["max"], 4.0)

    def test_enforce_rubric_coverage_clamps_earned_to_rubric_max(self) -> None:
        response = {
            "normalized_score_10": 10,
            "status": "AC",
            "criteria_scores": [
                {
                    "criterion": "Tối ưu độ phức tạp",
                    "earned": 9,
                    "max": 10,
                    "feedback": "ok",
                    "evidence": "ok",
                }
            ],
        }
        rubric_context = {
            "criteria": [{"name": "Tối ưu độ phức tạp", "max_score": 5}]
        }

        updated = AIGradingService._enforce_rubric_coverage(response, rubric_context)

        self.assertEqual(updated["criteria_scores"][0]["earned"], 5.0)
        self.assertEqual(updated["criteria_scores"][0]["max"], 5.0)
        self.assertEqual(updated["normalized_score_10"], 10.0)
        self.assertEqual(updated["status"], "AC")

    def test_parse_default_suggestions_are_positive_first(self) -> None:
        response = {
            "normalized_score_10": 4.5,
            "status": "WA",
            "criteria_scores": [],
            "technical_review": "Cần cải thiện xử lý biên.",
            "evidence_based_issues": [],
            "actionable_suggestions": [],
            "big_o": "O(n)",
        }

        result = AIGradingService._parse(response, "bai.py")

        self.assertIsNotNone(result.improvement)
        self.assertIn("Em đã", result.improvement)


if __name__ == "__main__":
    unittest.main()
