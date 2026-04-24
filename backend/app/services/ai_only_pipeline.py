import logging
from typing import Any, Callable, Dict, List, Optional

from app.core.models import GradingResult

logger = logging.getLogger("dsa.services.ai_only_pipeline")


RubricResolver = Callable[[str, str, str, Optional[str], Optional[List[Dict[str, Any]]]], Optional[Dict[str, Any]]]
RubricLoader = Callable[[Optional[str], str], Optional[Dict[str, Any]]]
RubricApplier = Callable[[GradingResult, Optional[Dict[str, Any]]], GradingResult]


class AIOnlyGradingPipeline:
    """Thin orchestration layer for the active AI-only grading path."""

    def __init__(
        self,
        ai_service: Any,
        resolve_rubric_profile: RubricResolver,
        load_rubric_profile: RubricLoader,
        apply_rubric: RubricApplier,
    ) -> None:
        self._ai = ai_service
        self._resolve_rubric_profile = resolve_rubric_profile
        self._load_rubric_profile = load_rubric_profile
        self._apply_rubric = apply_rubric

    async def grade_file(
        self,
        code: str,
        filename: str,
        topic: str,
        assignment_code: Optional[str] = None,
        baitap_dataset: Optional[List[Dict[str, Any]]] = None,
    ) -> GradingResult:
        """Run the AI-only grading flow with rubric resolution and normalization."""
        if self._ai is None:
            raise RuntimeError("AI-only grading mode requires a configured AI provider")

        rubric_profile = self._resolve_rubric_profile(
            code,
            filename,
            topic,
            assignment_code,
            baitap_dataset,
        )
        if not rubric_profile:
            rubric_profile = self._load_rubric_profile(assignment_code, topic)

        ai_result = await self._ai.grade_with_ai(
            code=code,
            filename=filename,
            topic=topic,
            ast_report=None,
            rubric_context=rubric_profile,
            strict_mode=True,
        )
        ai_result.code = code
        ai_result.language = "python"
        return self._apply_rubric(ai_result, rubric_profile)
