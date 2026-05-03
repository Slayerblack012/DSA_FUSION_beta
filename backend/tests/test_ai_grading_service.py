import unittest

from app.db.repositories.legacy_repository import LegacyRepository
from app.core.models import GradingResult
from app.services.ai_only_pipeline import AIOnlyGradingPipeline
from app.services.ai_grading_service import AIGradingService


class AIGradingServiceRubricCoverageTests(unittest.TestCase):
    def test_enforce_rubric_coverage_adds_missing_criteria_and_recomputes_score(
        self,
    ) -> None:
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
        rubric_context = {"criteria": [{"name": "Tối ưu độ phức tạp", "max_score": 5}]}

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

    def test_parse_strictly_removes_criteria_outside_rubric(self) -> None:
        response = {
            "normalized_score_10": 8.0,
            "status": "AC",
            "criteria_scores": [
                {
                    "criterion": "Đúng thuật toán",
                    "earned": 4,
                    "max": 6,
                    "feedback": "ok",
                    "evidence": "ok",
                },
                {
                    "criterion": "Tiêu chí ngoài rubric",
                    "earned": 2,
                    "max": 4,
                    "feedback": "ok",
                    "evidence": "ok",
                },
            ],
            "technical_review": "Đủ ổn.",
            "evidence_based_issues": [],
            "actionable_suggestions": ["Em làm tốt."],
            "big_o": "O(n)",
        }
        rubric_context = {
            "criteria": [
                {"name": "Đúng thuật toán", "max_score": 6},
            ]
        }

        result = AIGradingService._parse(
            response, "bai.py", rubric_context=rubric_context
        )

        self.assertIsNotNone(result.criteria_scores)
        self.assertEqual(len(result.criteria_scores), 1)
        self.assertEqual(result.criteria_scores[0]["criterion"], "Đúng thuật toán")

    def test_enforce_rubric_coverage_splits_legacy_packed_names(self) -> None:
        packed_name = (
            "name:Xac dinh dung do phuc tap la O(n),points:25,"
            "name:Thiet lap duoc so lan lap chinh xac la n/5,points:25,"
            "name:Giai thich ro quy tac loai bo hang so nhan trong Big O,points:25,"
            "name:Phan biet duoc su khac nhau giua so lan lap thuc te va bac tang truong thuat toan,points:25"
        )
        response = {
            "normalized_score_10": 8.0,
            "status": "AC",
            "criteria_scores": [
                {
                    "criterion": "Xac dinh dung do phuc tap la O(n)",
                    "earned": 25,
                    "max": 25,
                },
                {
                    "criterion": "Thiet lap duoc so lan lap chinh xac la n/5",
                    "earned": 20,
                    "max": 25,
                },
                {
                    "criterion": "Giai thich ro quy tac loai bo hang so nhan trong Big O",
                    "earned": 20,
                    "max": 25,
                },
                {
                    "criterion": "Phan biet duoc su khac nhau giua so lan lap thuc te va bac tang truong thuat toan",
                    "earned": 15,
                    "max": 25,
                },
            ],
        }

        updated = AIGradingService._enforce_rubric_coverage(
            response,
            {"criteria": [{"name": packed_name, "max_score": 100}]},
        )

        self.assertEqual(len(updated["criteria_scores"]), 4)
        self.assertEqual(updated["normalized_score_10"], 8.0)
        self.assertEqual(updated["criteria_scores"][0]["earned"], 25.0)

    def test_legacy_repository_splits_comma_packed_criteria(self) -> None:
        repo = LegacyRepository.__new__(LegacyRepository)
        raw = (
            "name:Xac dinh dung do phuc tap la O(n),points:25,"
            "name:Thiet lap duoc so lan lap chinh xac la n/5,points:25,"
            "name:Giai thich ro quy tac loai bo hang so nhan trong Big O,points:25,"
            "name:Phan biet duoc su khac nhau giua so lan lap thuc te va bac tang truong thuat toan,points:25"
        )

        parts = repo._split_criteria_text(raw)

        self.assertEqual(len(parts), 4)
        self.assertIn("Xac dinh dung do phuc tap la O(n)", parts[0])
        self.assertIn("(25d)", parts[0])


class AIOnlyGradingPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_grade_file_uses_non_strict_mode_for_ai_provider(self) -> None:
        class DummyAIService:
            def __init__(self) -> None:
                self.calls = []

            async def grade_with_ai(self, **kwargs):
                self.calls.append(kwargs)
                return GradingResult(
                    filename=kwargs["filename"],
                    total_score=7.5,
                    status="AC",
                    algorithms_detected=["dfs"],
                    feedback="ok",
                    time_used=1.0,
                    memory_used=1.0,
                )

        dummy_ai = DummyAIService()
        pipeline = AIOnlyGradingPipeline(
            ai_service=dummy_ai,
            resolve_rubric_profile=lambda *args, **kwargs: None,
            load_rubric_profile=lambda *args, **kwargs: None,
            apply_rubric=lambda result, rubric: result,
        )

        result = await pipeline.grade_file(
            code="print('hi')",
            filename="main.py",
            topic="sorting",
        )

        self.assertEqual(len(dummy_ai.calls), 1)
        self.assertFalse(dummy_ai.calls[0]["strict_mode"])
        self.assertEqual(result.filename, "main.py")
        self.assertEqual(result.language, "python")
        self.assertEqual(result.code, "print('hi')")


if __name__ == "__main__":
    unittest.main()
