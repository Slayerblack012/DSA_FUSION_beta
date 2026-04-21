"""
DSA AutoGrader - Grading Service (Orchestrator).

Coordinates the full grading pipeline:
  1. AST analysis  (primary — always works)
  2. AI grading    (optional — only if API key is set)
  3. Plagiarism check
"""

import logging
import asyncio
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional

from app.core.config import MAX_CONCURRENT_AI_CALLS
from app.core.models import GradingResult
from app.services.ai_grading_service import AIGradingService
from app.services.ast_grader import DSALightningGrader
from app.services.plagiarism_service import PlagiarismService
from app.services.grading.criteria_matcher import criteria_matcher

logger = logging.getLogger("dsa.services.grading")


_BREAKDOWN_MAPPING = {
    "tests": "Testing (Dynamic Tests)",
    "dsa": "Data Structures & Algorithms",
    "pep8": "Code Style (PEP8)",
    "complexity": "Optimization (Complexity)"
}

_IMPROVEMENT_KEYWORDS = ["should", "consider", "need", "optimize", "style", "naming", "blank line", "avoid"]

_COMPONENT_MAX = {
    "tests": 4.0,
    "dsa": 6.0,
    "pep8": 1.0,
    "complexity": 1.0,
}

_WEIGHT_AI = 1.00
_WEIGHT_AST = 0.00
_WEIGHT_ALGORITHM = 0.00
_WEIGHT_CONSTRAINT = 0.00
_SCORING_POLICY_VERSION = "policy_v2_70_20_5_5"
_BAITAP_MIN_CODE = "CTDL"
_RUBRIC_MATCH_MIN_SCORE = 3.0
_RUBRIC_MATCH_MIN_MARGIN = 0.75
# When low-confidence rubric match, fall back to AST-only scoring instead of
# forcing a potentially wrong rubric onto the submission.
_RUBRIC_LOW_CONFIDENCE_FALLBACK = True

_RUBRIC_COMPONENT_KEYWORDS = {
    "tests": ["test", "kiểm thử", "case", "correct", "đúng", "chính xác", "output"],
    "dsa": ["algorithm", "thuật toán", "dsa", "data structure", "cấu trúc dữ liệu", "logic"],
    "pep8": ["style", "pep8", "format", "readability", "naming", "coding convention", "trình bày"],
    "complexity": ["complexity", "big o", "optimization", "hiệu năng", "tối ưu", "time", "memory"],
}

class GradingService:
    """
    Main grading orchestrator.
    """

    def __init__(
        self,
        ast_service: DSALightningGrader,
        ai_service: AIGradingService,
        plagiarism_service: PlagiarismService,
        repository: Any,
        job_store: Any,
        event_bus: Any,
    ) -> None:
        self._ast = ast_service
        self._ai = ai_service
        self._plagiarism = plagiarism_service
        self._repository = repository
        self._job_store = job_store
        self._event_bus = event_bus
        self._ai_enabled = True  # Enabled for hybrid grading
        self._criteria_matcher = criteria_matcher

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------
    async def grade_submission(
        self,
        files: List[tuple],
        topic: str,
        student_name: str,
        student_id: Optional[str] = None,
        assignment_code: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Grade a batch of files and return aggregated results."""
        start = time.time()
        logger.info(
            "Grading %d file(s) | Student: %s (%s) | Topic: %s",
            len(files), student_name, student_id or "N/A", topic or "Auto",
        )

        if not hasattr(self, "_baitap_cache") or time.time() - getattr(self, "_baitap_cache_time", 0) > 300:
            self._baitap_cache = self._load_baitap_dataset()
            self._baitap_cache_time = time.time()
        baitap_dataset = self._baitap_cache

        # Process files concurrently with semaphore limit
        # Concurrency limit tied to AI call capacity (prevents resource exhaustion)
        # BEFORE: Semaphore(50) → 50 concurrent subprocesses = OOM risk
        # AFTER:  Semaphore(10) → controlled concurrency
        max_concurrent = max(5, MAX_CONCURRENT_AI_CALLS * 2)
        semaphore = asyncio.Semaphore(max_concurrent)
        total_files = len(files)
        completed_count = 0

        async def _grade_safe(fname: str, fcode: str) -> GradingResult:
            async with semaphore:
                try:
                    res = await self.grade_single_file(
                        fcode,
                        fname,
                        topic,
                        assignment_code=assignment_code,
                        baitap_dataset=baitap_dataset,
                    )
                except Exception as exc:
                    logger.error("Failed to grade %s: %s", fname, exc)
                    res = self._error_result(fname, str(exc))
                
                res.student_name = student_name
                res.student_id = student_id

                # Update progress — throttle: every file for small batches,
                # every 5 files for large batches (≥20), to reduce job_store contention.
                nonlocal completed_count
                completed_count += 1
                update_interval = 1 if total_files < 20 else 5
                if job_id and self._job_store and (
                    completed_count % update_interval == 0 or completed_count == total_files
                ):
                    try:
                        job_data = await self._job_store.get(job_id)
                        if job_data:
                            job_data["progress"] = {
                                "current": completed_count,
                                "total": total_files,
                                "percent": int((completed_count / total_files) * 100)
                            }
                            await self._job_store.set(job_id, job_data)
                    except Exception as exc:
                        logger.warning("Progress update failed: %s", exc)

                return res

        tasks = [_grade_safe(fn, fc) for fn, fc in files]
        results: List[GradingResult] = await asyncio.gather(*tasks)

        # Plagiarism check
        plagiarism_alerts = await self.check_plagiarism(results, assignment_code)

        # Summary
        elapsed = time.time() - start
        scores = [r.total_score for r in results if r.total_score is not None]
        avg = round(sum(scores) / len(scores), 1) if scores else None

        # Save to DB
        saved_db_count = self._save_to_database(
            results, job_id, student_name, student_id, topic, assignment_code
        )

        summary = {
            "total_files": len(results),
            "avg_score": avg,
            "total_time": f"{elapsed:.1f}s",
            "plagiarism_alerts": len(plagiarism_alerts),
            "saved_to_db": saved_db_count,
        }
        logger.info("Grading completed: %s", summary)

        # Publish events to event bus (fire-and-forget, non-blocking)
        if self._event_bus:
            try:
                from app.core.models import Event, EventType
                await self._event_bus.publish(Event(
                    type=EventType.JOB_COMPLETED,
                    payload={
                        "job_id": job_id,
                        "student_name": student_name,
                        "student_id": student_id,
                        "topic": topic,
                        "assignment_code": assignment_code,
                        "summary": summary,
                    },
                    source="grading_service",
                    timestamp=time.time(),
                ))
                if plagiarism_alerts:
                    await self._event_bus.publish(Event(
                        type=EventType.PLAGIARISM_DETECTED,
                        payload={
                            "job_id": job_id,
                            "student_name": student_name,
                            "alerts": plagiarism_alerts,
                        },
                        source="grading_service",
                        timestamp=time.time(),
                    ))
            except Exception as exc:
                logger.warning("Event bus publish failed (non-critical): %s", exc)

        return {
            "results": [self._to_dict(r) for r in results],
            "summary": summary,
            "plagiarism_alerts": plagiarism_alerts,
        }

    def _save_to_database(
        self,
        results: List[GradingResult],
        job_id: Optional[str],
        student_name: str,
        student_id: Optional[str],
        topic: str,
        assignment_code: Optional[str]
    ) -> int:
        """Save all grading results to database."""
        if not self._repository or not results:
            return 0

        dicts_to_save = []
        for r in results:
            d = self._to_dict(r)
            d["job_id"] = job_id or ""
            d["student_name"] = student_name
            d["student_id"] = student_id or ""
            d["topic"] = topic
            # Enrich with test summary so DB has aggregated pass rate
            test_results = d.get("test_results") or []
            if test_results:
                test_passed = sum(1 for t in test_results if t.get("passed"))
                test_total = len(test_results)
                d["test_summary"] = {
                    "total": test_total,
                    "passed": test_passed,
                    "failed": test_total - test_passed,
                    "pass_rate": round(test_passed / test_total, 4),
                }
            dicts_to_save.append(d)

        try:
            saved_ids = self._repository.save_batch_results(dicts_to_save, assignment_code)
            logger.info("[SUCCESS] Saved %d submissions to database", len(saved_ids))
            return len(saved_ids)
        except Exception as e:
            logger.error("[ERROR] Failed to save batch to db: %s", e)
            # Fallback: save one by one to maximise persistence
            saved_count = 0
            for result_dict in dicts_to_save:
                try:
                    self._repository.save_result(result_dict)
                    saved_count += 1
                except Exception as e2:
                    logger.error("[ERROR] Failed to save individual submission (%s): %s",
                                 result_dict.get("filename", "?"), e2)
            return saved_count

    async def grade_single_file(
        self,
        code: str,
        filename: str,
        topic: str,
        assignment_code: Optional[str] = None,
        baitap_dataset: Optional[List[Dict[str, Any]]] = None,
    ) -> GradingResult:
        """Grade a single file through AST pipeline (+ AI optional)."""
        logger.debug("Grading: %s", filename)

        # Step 1 — AST analysis (always runs)
        try:
            from starlette.concurrency import run_in_threadpool
            ast_result = await run_in_threadpool(
                self._ast.grade_file_ultra_fast, code, filename, topic
            )
        except Exception as exc:
            logger.error("AST grading failed for %s: %s", filename, exc)
            return self._error_result(filename, f"AST analysis error: {str(exc)}")

        # Parse algorithms from AST result
        raw_algorithms = ast_result.get("algorithms", [])
        if isinstance(raw_algorithms, str):
            detected_algorithms = [a.strip() for a in raw_algorithms.split(",") if a.strip()]
        else:
            detected_algorithms = list(raw_algorithms) if raw_algorithms else []

        # Prefer deterministic exercise-level rubric profile (DB BAITAP) when available.
        selected_rubric_profile = self._select_rubric_profile_for_submission(
            code=code,
            filename=filename,
            topic=topic,
            assignment_code=assignment_code,
            ast_result=ast_result,
            baitap_dataset=baitap_dataset,
        )

        # Step 1.5 — Precise criteria matching
        # Load rubric criteria from DB
        if selected_rubric_profile and selected_rubric_profile.get("criteria"):
            matched_assignment_code = (
                ((selected_rubric_profile.get("matched_exercise") or {}).get("assignment_code"))
                or selected_rubric_profile.get("assignment_code")
            )

            exact_rows = []
            if matched_assignment_code and self._repository:
                try:
                    exact_rows = self._repository.get_baitap_criteria(
                        matched_assignment_code,
                        None,
                        include_from_assignment=False,
                        split_packed_criteria=True,
                    )
                except Exception as exc:
                    logger.warning("Cannot load exact BAITAP criteria for %s: %s", matched_assignment_code, exc)

            if exact_rows:
                rubric_criteria = exact_rows
            else:
                rubric_criteria = [
                    {
                        "name": item.get("name") or item.get("criteria_name") or "",
                        "description": item.get("description") or "",
                        "max_score": float(item.get("max_score") or 0),
                        "source_text": item.get("source_text") or item.get("name") or "",
                        "criteria_code": item.get("criteria_code") or item.get("criterion_code") or "",
                    }
                    for item in (selected_rubric_profile.get("criteria") or [])
                    if isinstance(item, dict)
                ]
        else:
            rubric_criteria = self._load_rubric_criteria(assignment_code, topic)

        # Match detected algorithms → rubric criteria
        matching_result = self._criteria_matcher.match(
            detected_algorithms=detected_algorithms,
            rubric_criteria=rubric_criteria,
            ast_breakdown=ast_result.get("breakdown", {}),
            test_results=ast_result.get("test_results", []),
        )

        if selected_rubric_profile:
            matching_result.matched_exercise = selected_rubric_profile.get("matched_exercise")
            matching_result.match_proof = selected_rubric_profile.get("match_proof")

        # Compute per-criterion scores
        criteria_scores = self._criteria_matcher.compute_scores(
            matching_result,
            ast_breakdown=ast_result.get("breakdown", {}),
            test_results=ast_result.get("test_results", []),
            rubric_criteria=rubric_criteria,
        )

        # Build rubric profile for AI (now with precise matches)
        rubric_profile = self._build_rubric_profile_from_matches(
            matching_result, criteria_scores, assignment_code, topic
        )

        logger.info(
            "Criteria match for %s: %d/%d criteria matched, algorithms=%s",
            filename,
            len(matching_result.matched_criteria),
            len(rubric_criteria) if rubric_criteria else 0,
            detected_algorithms,
        )

        # Step 2 — AI grading (optional)
        if self._ai_enabled:
            try:
                ai_result = await self._ai.grade_with_ai(
                    code=code,
                    filename=filename,
                    topic=topic,
                    ast_report=ast_result,
                    rubric_context=rubric_profile,
                )
                merged = self._combine(ast_result, ai_result, code, rubric_profile=rubric_profile)
                return self._apply_rubric_to_result(merged, rubric_profile)
            except Exception as exc:
                logger.warning("AI grading failed, falling back to AST: %s", exc)

        ast_only = self._ast_to_result(ast_result, filename, code, rubric_profile=rubric_profile)
        return self._apply_rubric_to_result(ast_only, rubric_profile)

    async def check_plagiarism(
        self,
        results: List[GradingResult],
        assignment_code: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Check plagiarism within and across submissions."""
        logger.info("Checking plagiarism for %d results.", len(results))

        intra = await self._plagiarism.check_intra_job_plagiarism(results)
        cross = await self._plagiarism.check_cross_job_plagiarism(results, assignment_code)
        alerts = intra + cross

        if alerts:
            logger.warning("Plagiarism detected: %d alerts.", len(alerts))
        return alerts

    # ------------------------------------------------------------------
    #  Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_score_10(raw_score: Any) -> float:
        """Normalize score to 0-10 scale (supports accidental 0-100 values).
        Guards against NaN, Inf, and None.
        """
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            return 0.0

        import math
        if math.isnan(score) or math.isinf(score):
            return 0.0

        if score > 10.0:
            score = score / 10.0

        return round(max(0.0, min(score, 10.0)), 1)

    def _ast_to_result(
        self,
        ast_result: Dict[str, Any],
        filename: str,
        code: str = "",
        rubric_profile: Optional[Dict[str, Any]] = None,
    ) -> GradingResult:
        """Convert AST result dict to GradingResult object."""
        score = self._normalize_score_10(ast_result.get("total_score", 0))
        # Respect TLE status from AST grader if present
        ast_status = ast_result.get("status", "")
        if ast_status == "TLE":
            status = "TLE"
        elif ast_status == "FLAG":
            status = "FLAG"
        else:
            status = "AC" if score >= 5.0 else "WA"

        algorithms = ast_result.get("algorithms", [])
        if isinstance(algorithms, str):
            algorithms = [a.strip() for a in algorithms.split(",") if a.strip()]

        ast_breakdown = ast_result.get("breakdown", {})
        breakdown = {
            "logic_score": ast_breakdown.get("tests", 0),
            "algorithm_score": ast_breakdown.get("dsa", 0),
            "style_score": ast_breakdown.get("pep8", 0),
            "optimization_score": ast_breakdown.get("complexity", 0),
        }

        test_results = ast_result.get("test_results", [])

        # If rubric profile has pre-computed criteria scores, use them
        criteria_scores = None
        if rubric_profile and rubric_profile.get("criteria_scores_computed"):
            criteria_scores = rubric_profile["criteria_scores_computed"]

        result = GradingResult(
            filename=filename,
            total_score=score,
            status=status,
            algorithms_detected=algorithms,
            feedback=self._ast_feedback(ast_result),
            time_used=ast_result.get("runtime_ms", 0.0) / 1000.0,
            memory_used=0.0,
            plagiarism_detected=False,
            has_rubric=True,
            breakdown=breakdown,
            reasoning="\n".join(ast_result.get("notes", [])),
            complexity=ast_result.get("complexity", "O(n)"),
            complexity_analysis=next((n for n in ast_result.get("notes", []) if "Hiệu năng:" in n), None),
            fingerprint="|".join(map(str, ast_result.get("fingerprint", []))) if isinstance(ast_result.get("fingerprint"), list) else None,
            code=code,
            language="python",
            test_results=test_results,
            complexity_curve=self._generate_complexity_curve(ast_result.get("complexity", "O(n)")),
            criteria_scores=criteria_scores,
            score_proof={
                "mode": "ast_only",
                "policy_version": _SCORING_POLICY_VERSION,
                "formula": "final = ast_score",
                "weights": {"ast": 1.0},
                "components": {
                    "ast_score": score,
                },
                "final_score": score,
            },
        )

        # Apply rubric adjustment if criteria scores are available
        if criteria_scores and rubric_profile:
            self._apply_criteria_scores_to_result(result, criteria_scores, rubric_profile)

        return result

    def _apply_criteria_scores_to_result(
        self,
        result: GradingResult,
        criteria_scores: List[Dict[str, Any]],
        rubric_profile: Dict[str, Any],
    ) -> None:
        """Apply pre-computed criteria scores to a GradingResult and adjust total score."""
        rubric_snapshot = self._build_rubric_snapshot(rubric_profile)
        result.rubric_snapshot = rubric_snapshot

        criteria_results = []
        total_points = 0.0
        total_weight = float(rubric_profile.get("total_max") or 0)

        for cs in criteria_scores:
            criterion_name = cs.get("criterion", "")
            max_s = float(cs.get("max", 0))
            earned = float(cs.get("earned", 0))
            earned = max(0.0, min(earned, max_s if max_s > 0 else earned))
            total_points += earned
            criteria_results.append({
                "name": criterion_name,
                "source_text": cs.get("source_text", criterion_name),
                "criteria_code": cs.get("criteria_code") or "",
                "earned": round(earned, 2),
                "max": round(max_s, 2),
                "feedback": cs.get("feedback", ""),
                "evidence": cs.get("evidence", ""),
            })

        if total_weight <= 0 and criteria_results:
            total_weight = sum(float(item.get("max") or 0) for item in criteria_results)

        before_rubric = result.total_score
        if total_weight > 0:
            result.total_score = round(min(max((total_points / total_weight) * 10.0, 0.0), 10.0), 1)
        result.status = "AC" if result.total_score >= 5.0 else "WA"
        result.has_rubric = True

        if isinstance(result.score_proof, dict):
            result.score_proof["rubric_adjustment"] = {
                "applied": True,
                "before": before_rubric,
                "after": result.total_score,
                "source": rubric_profile.get("source", "criteria_matcher"),
                "criteria_results": criteria_results,
                "matched_exercise": rubric_profile.get("matched_exercise"),
                "match_proof": rubric_profile.get("match_proof"),
            }
            result.score_proof["rubric_snapshot"] = rubric_snapshot

    @staticmethod
    def _ast_feedback(ast_result: Dict[str, Any]) -> str:
        """Build student-friendly feedback from AST result in Vietnamese."""
        lines = ["## Kết quả chấm điểm chi tiết\n"]
        score = ast_result.get("total_score", 0)

        breakdown = ast_result.get("breakdown", {})
        if breakdown:
            lines.append("### Phân bổ điểm số:")
            for cat, val in breakdown.items():
                label = _BREAKDOWN_MAPPING.get(cat, cat)
                # Simple translation for categories
                labels_vn = {
                    "tests": "Kiểm thử (Dynamic Tests)",
                    "dsa": "Cấu trúc dữ liệu & Thuật toán",
                    "pep8": "Phong cách lập trình (PEP8)",
                    "complexity": "Tối ưu hóa (Complexity)"
                }
                lines.append(f"- **{labels_vn.get(cat, label)}**: {val} điểm")

        algos = ast_result.get("algorithms", [])
        if algos:
            label = ", ".join(algos) if isinstance(algos, list) else algos
            lines.append(f"\n### Thuật toán phát hiện: `{label}`")

        notes = ast_result.get("notes", [])
        if notes:
            main_notes = []
            improvements = []

            for n in notes:
                if any(x in n for x in ["/10", "đ)"]):
                    continue
                if any(kw in n.lower() for kw in _IMPROVEMENT_KEYWORDS):
                    improvements.append(n)
                else:
                    main_notes.append(n)

            if main_notes:
                lines.append("\n### Nhận xét & Đánh giá:")
                for n in main_notes:
                    lines.append(f"- {n}")

            if improvements:
                lines.append("\n### Gợi ý cải thiện:")
                for n in improvements:
                    lines.append(f"- {n}")
            elif score >= 9.0:
                lines.append("\n### Gợi ý cải thiện:")
                lines.append("- Mã nguồn của em rất tốt. Hãy thử thách với các bộ dữ liệu lớn hơn hoặc tối ưu bộ nhớ.")

        if score >= 8.0:
            lines.append("\n**XUẤT SẮC!** Mã nguồn của em rất chất lượng.")
        elif score >= 5.0:
            lines.append("\n**ĐẠT YÊU CẦU.** Em có thể tối ưu thêm mã nguồn của mình.")
        else:
            lines.append("\n**CẦN CỐ GẮNG.** Hãy xem các nhận xét bên trên để cải thiện bài làm.")

        return "\n".join(lines)

    def _load_rubric_profile(self, assignment_code: Optional[str], topic: str) -> Optional[Dict[str, Any]]:
        """Load rubric criteria from DB and prepare a profile for runtime scoring."""
        if not self._repository:
            return None

        # Priority 1: SQL Server table dbo.BAITAP (requested production source)
        baitap_rows: List[Dict[str, Any]] = []
        try:
            # Requested behavior: always grade against the full BAITAP criteria
            # set starting from CTDL_D1_01 to the end of dataset.
            baitap_rows = self._repository.get_baitap_criteria(
                _BAITAP_MIN_CODE,
                None,
                include_from_assignment=True,
            )
        except Exception as exc:
            logger.warning("Cannot load rubric from dbo.BAITAP: %s", exc)

        if baitap_rows:
            criteria = []
            total_max = 0.0

            for item in baitap_rows:
                max_score = float(item.get("max_score") or 0)
                if max_score <= 0:
                    continue

                name = (item.get("criteria_name") or "Tiêu chí").strip()
                description = (item.get("description") or "").strip()
                component_hint = (item.get("component") or "").strip().lower()

                if component_hint:
                    components = self._map_rubric_components(component_hint, description)
                else:
                    components = self._map_rubric_components(name, description)

                total_max += max_score
                criteria.append(
                    {
                        "name": name,
                        "source_text": name,
                        "criteria_code": item.get("criteria_code") or item.get("criterion_code") or "",
                        "description": description,
                        "max_score": max_score,
                        "components": components,
                    }
                )

            if criteria and total_max > 0:
                return {
                    "source": "dbo.BAITAP",
                    "assignment_code": assignment_code,
                    "topic": topic,
                    "criteria": criteria,
                    "total_max": total_max,
                }

        return None

    def _load_rubric_criteria(self, assignment_code: Optional[str], topic: str) -> List[Dict[str, Any]]:
        """Load rubric criteria from DB as a flat list for criteria matching."""
        if not self._repository:
            return []

        # Try loading from dbo.BAITAP
        try:
            baitap_rows = self._repository.get_baitap_criteria(
                _BAITAP_MIN_CODE,
                None,
                include_from_assignment=True,
            )
            if baitap_rows:
                return baitap_rows
        except Exception as exc:
            logger.warning("Cannot load rubric criteria from dbo.BAITAP: %s", exc)

        return []

    def _build_rubric_profile_from_matches(
        self,
        matching_result: Any,
        criteria_scores: List[Dict[str, Any]],
        assignment_code: Optional[str],
        topic: str,
    ) -> Dict[str, Any]:
        """Build rubric profile from criteria matching results for AI consumption."""
        criteria = []
        total_max = 0.0

        for cs in criteria_scores:
            max_s = cs.get("max", 10.0)
            total_max += max_s
            criteria.append({
                "name": cs["criterion"],
                "source_text": cs.get("source_text", cs["criterion"]),
                "criteria_code": cs.get("criteria_code") or "",
                "description": "",
                "max_score": max_s,
            })

        return {
            "source": "criteria_matcher",
            "assignment_code": assignment_code,
            "topic": topic,
            "criteria": criteria,
            "total_max": total_max,
            "matched_exercise": matching_result.matched_exercise,
            "match_proof": matching_result.match_proof,
            "criteria_scores_computed": criteria_scores,
        }

    @staticmethod
    def _build_rubric_snapshot(rubric_profile: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not rubric_profile:
            return None

        criteria = []
        for item in rubric_profile.get("criteria", []) or []:
            if not isinstance(item, dict):
                continue
            criteria.append({
                "name": item.get("name") or item.get("criteria_name") or "",
                "source_text": item.get("source_text") or item.get("name") or item.get("criteria_name") or "",
                "criteria_code": item.get("criteria_code") or item.get("criterion_code") or "",
                "description": item.get("description") or "",
                "max_score": item.get("max_score") or 0,
                "components": item.get("components") or [],
            })

        return {
            "source": rubric_profile.get("source", "database"),
            "assignment_code": rubric_profile.get("assignment_code"),
            "topic": rubric_profile.get("topic"),
            "total_max": rubric_profile.get("total_max", 0),
            "matched_exercise": rubric_profile.get("matched_exercise"),
            "match_proof": rubric_profile.get("match_proof"),
            "criteria": criteria,
        }

    def _load_baitap_dataset(self) -> List[Dict[str, Any]]:
        """Load normalized BAITAP exercises from CTDL_D1_01 onward."""
        if not self._repository:
            return []
        try:
            data = self._repository.get_baitap_exercises(_BAITAP_MIN_CODE)
            if isinstance(data, list):
                return data
        except Exception as exc:
            logger.warning("Cannot load BAITAP exercise dataset: %s", exc)
        return []

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).lower().strip()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", text)

    @staticmethod
    def _tokenize_text(value: Any) -> List[str]:
        normalized = GradingService._normalize_text(value)
        return [t for t in re.split(r"[^a-z0-9_]+", normalized) if len(t) >= 2]

    def _build_profile_from_exercise(self, exercise: Dict[str, Any], topic: str) -> Optional[Dict[str, Any]]:
        criteria_items = exercise.get("criteria") or []
        if not criteria_items:
            return None

        max_per_item = round(10.0 / len(criteria_items), 2)
        criteria = []
        total_max = 0.0

        for item in criteria_items:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("criteria_name") or item.get("description") or "").strip()
                desc = str(item.get("description") or item.get("requirement") or "").strip()
                item_max = float(item.get("max_score") or max_per_item)
            else:
                name = str(item).strip()
                desc = ""
                item_max = max_per_item
            
            if not name:
                continue

            criteria.append(
                {
                    "name": name,
                    "source_text": name,
                    "criteria_code": f"{exercise.get('assignment_code')}_C{len(criteria)+1}",
                    "description": desc,
                    "max_score": item_max,
                    "components": self._map_rubric_components(
                        name,
                        desc,
                    ),
                }
            )
            total_max += item_max

        if not criteria or total_max <= 0:
            return None

        return {
            "source": "dbo.BAITAP:matched_by_code",
            "assignment_code": exercise.get("assignment_code"),
            "topic": topic,
            "criteria": criteria,
            "total_max": total_max,
            "matched_exercise": {
                "assignment_code": exercise.get("assignment_code"),
                "title": exercise.get("title"),
            },
        }

    def _select_rubric_profile_for_submission(
        self,
        code: str,
        filename: str,
        topic: str,
        assignment_code: Optional[str],
        ast_result: Dict[str, Any],
        baitap_dataset: Optional[List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """Deterministically match submitted code to the most relevant BAITAP exercise."""
        dataset = baitap_dataset or []
        if not dataset:
            return None

        if assignment_code:
            target = self._normalize_text(assignment_code)
            for ex in dataset:
                if self._normalize_text(ex.get("assignment_code")) == target:
                    exact_profile = self._build_profile_from_exercise(ex, topic)
                    if exact_profile:
                        return exact_profile

        ast_algos = ast_result.get("algorithms", [])
        if isinstance(ast_algos, str):
            ast_algos = [x.strip() for x in ast_algos.split(",") if x.strip()]

        sub_text_parts = [
            filename,
            topic,
            " ".join(ast_algos),
            ast_result.get("complexity", ""),
            code[:2000],
        ]
        sub_terms = set(self._tokenize_text(" ".join(str(x) for x in sub_text_parts if x)))
        complexity_hint = self._normalize_text(ast_result.get("complexity", ""))

        scored: List[Dict[str, Any]] = []
        for ex in dataset:
            ex_blob = " ".join(
                [
                    str(ex.get("assignment_code") or ""),
                    str(ex.get("title") or ""),
                    str(ex.get("description") or ""),
                    str(ex.get("requirement") or ""),
                    " ".join(str(c) for c in (ex.get("criteria") or [])),
                ]
            )
            ex_norm = self._normalize_text(ex_blob)
            ex_terms = set(self._tokenize_text(ex_blob))

            overlap = len(sub_terms & ex_terms)
            union = max(1, len(sub_terms | ex_terms))
            jaccard = overlap / union

            score = overlap * 0.5 + jaccard * 10.0
            if complexity_hint and complexity_hint in ex_norm:
                score += 2.0

            if ast_algos:
                algo_hits = 0
                for algo in ast_algos:
                    algo_tokens = [t for t in self._tokenize_text(algo) if len(t) >= 3]
                    if algo_tokens and all(tok in ex_norm for tok in algo_tokens[:2]):
                        algo_hits += 1
                score += min(3.0, algo_hits * 1.2)

            scored.append({"exercise": ex, "score": score})

        if not scored:
            return None

        scored.sort(key=lambda x: x["score"], reverse=True)
        best = scored[0]
        second = scored[1] if len(scored) > 1 else {"score": 0.0}
        margin = float(best["score"]) - float(second["score"])

        low_confidence = float(best["score"]) < _RUBRIC_MATCH_MIN_SCORE or margin < _RUBRIC_MATCH_MIN_MARGIN
        if low_confidence:
            logger.warning(
                "Rubric auto-match low confidence for %s (best=%.2f, margin=%.2f). %s",
                filename,
                float(best["score"]),
                margin,
                "Skipping rubric to avoid wrong scoring." if _RUBRIC_LOW_CONFIDENCE_FALLBACK else "Using top candidate anyway.",
            )
            if _RUBRIC_LOW_CONFIDENCE_FALLBACK:
                return None

        profile = self._build_profile_from_exercise(best["exercise"], topic)
        if profile:
            profile["match_proof"] = {
                "score": round(float(best["score"]), 4),
                "margin": round(margin, 4),
                "low_confidence": low_confidence,
            }
        return profile

    @staticmethod
    def _map_rubric_components(criteria_name: str, description: str) -> List[str]:
        """Map a rubric criterion to grading components.

        Uses keyword matching against _RUBRIC_COMPONENT_KEYWORDS.
        Returns all matched components; if none match, returns all components
        so the criterion is treated as an overall/holistic criterion.
        """
        text = f"{criteria_name} {description}".lower()
        mapped = []

        for comp, keywords in _RUBRIC_COMPONENT_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                mapped.append(comp)

        # If no keyword matched, treat as holistic — all components contribute equally
        if not mapped:
            mapped = list(_RUBRIC_COMPONENT_KEYWORDS.keys())

        return mapped

    def _apply_rubric_to_result(self, result: GradingResult, rubric_profile: Optional[Dict[str, Any]]) -> GradingResult:
        """Sửa lỗi: Hiện tiêu đề, xóa thanh rác 10/10, hiện box bằng chứng."""
        if not rubric_profile:
            return result

        # 1. HIỆN LẠI TIÊU ĐỀ: Gán snapshot cho Frontend đọc metadata
        rubric_snapshot = GradingService._build_rubric_snapshot(rubric_profile)
        result.rubric_snapshot = rubric_snapshot
        result.has_rubric = True

        ai_raw_scores = getattr(result, "criteria_scores", None) or []
        db_criteria = rubric_profile.get("criteria", [])

        if db_criteria:
            criteria_results = []
            total_points = 0.0
            actual_total_weight = 0.0

            used_ai_indices = set()

            # 2. CHỈ LẤY TIÊU CHÍ DB: Duyệt chính xác theo danh sách SQL
            for i, db_item in enumerate(db_criteria):
                db_name = db_item.get("name") or db_item.get("criteria_name") or ""
                db_max = float(db_item.get("max_score") or 2.5)
                
                matched_ai = None
                db_norm = self._normalize_text(db_name)
                
                # Khớp điểm từ AI (Loại bỏ các dòng summary rác)
                best_match_idx = -1
                for idx, ai_item in enumerate(ai_raw_scores):
                    if idx in used_ai_indices:
                        continue
                    ai_name = self._normalize_text(ai_item.get("criterion", ""))
                    if ai_name and ai_name not in ["criterion", "total", "score", "normalized"]:
                        if ai_name == db_norm:
                            best_match_idx = idx
                            break
                        elif ai_name in db_norm or db_norm in ai_name:
                            best_match_idx = idx
                
                if best_match_idx != -1:
                    matched_ai = ai_raw_scores[best_match_idx]
                    used_ai_indices.add(best_match_idx)
                
                earned = 0.0
                fb = f"AI chưa cung cấp đánh giá chi tiết cho tiêu chí: {db_name}."
                ev = "AI thực hiện đánh giá trực tiếp dựa trên nội dung mã nguồn."

                if matched_ai:
                    try:
                        earned = float(matched_ai.get("earned") or 0.0)
                    except Exception:
                        earned = 0.0
                    earned = max(0.0, min(earned, db_max))
                    fb = matched_ai.get("feedback") or fb
                    ev = matched_ai.get("evidence") or ev

                total_points += earned
                actual_total_weight += db_max
                criteria_results.append({
                    "name": db_name, "earned": round(earned, 2), "max": round(db_max, 2),
                    "feedback": fb, "evidence": ev,
                })

            # 3. CẬP NHẬT ĐIỂM FILE
            if actual_total_weight > 0:
                result.total_score = round(min((total_points / actual_total_weight) * 10.0, 10.0), 1)
            
            result.status = "AC" if result.total_score >= 5.0 else "WA"
            result.criteria_scores = criteria_results 

            # 4. HIỆN BOX BẰNG CHỨNG: Cấp đúng key criteria_results cho Frontend
            if not isinstance(result.score_proof, dict):
                result.score_proof = {}
            result.score_proof["rubric_adjustment"] = {
                "applied": True,
                "after": result.total_score,
                "criteria_results": criteria_results,
                "matched_exercise": rubric_profile.get("matched_exercise")
            }

            # Gộp text feedback
            lines = ["### CHI TIẾT CHẤM ĐIỂM:"]
            for item in criteria_results:
                lines.append(f"- {item['name']}: {item['earned']}/{item['max']}đ")
            result.feedback = (result.reasoning or "") + "\n" + "\n".join(lines)

            return result
        return result

    @staticmethod
    def _combine(
        ast_result: Dict[str, Any],
        ai_result: GradingResult,
        code: str,
        rubric_profile: Optional[Dict[str, Any]] = None,
    ) -> GradingResult:
        """Merge AST and AI results with configured weighted scoring."""
        ast_score = GradingService._normalize_score_10(ast_result.get("total_score", 0))
        ai_score = GradingService._normalize_score_10(ai_result.total_score or 0)

        rubric_scores = getattr(ai_result, "criteria_scores", None) or []

        # Fallback: if AI didn't provide criteria scores, use pre-computed ones from rubric_profile
        if not rubric_scores and rubric_profile and rubric_profile.get("criteria_scores_computed"):
            rubric_scores = rubric_profile["criteria_scores_computed"]

        if rubric_scores:
            raw_scores = []
            for item in rubric_scores:
                if not isinstance(item, dict):
                    continue
                criterion = str(item.get("criterion") or "").strip()
                if not criterion:
                    continue
                try:
                    earned = float(item.get("earned") or 0.0)
                except (TypeError, ValueError):
                    earned = 0.0
                try:
                    max_score = float(item.get("max") or item.get("max_score") or 0.0)
                except (TypeError, ValueError):
                    max_score = 0.0
                if max_score <= 0:
                    continue
                earned = max(0.0, min(earned, max_score))
                raw_scores.append({
                    "criterion": criterion,
                    "earned": round(earned, 2),
                    "max": round(max_score, 2),
                    "criteria_code": str(item.get("criteria_code") or item.get("criterion_code") or "").strip(),
                    "feedback": str(item.get("feedback") or "").strip(),
                    "evidence": str(item.get("evidence") or "").strip(),
                })

            cleaned_scores = []
            total_points = 0.0
            total_max = 0.0

            rubric_items = (rubric_profile or {}).get("criteria") or []
            if rubric_items:
                used_indexes = set()

                def _find_best_ai_score_idx(rubric_name: str) -> Optional[int]:
                    rubric_key = GradingService._normalize_text(rubric_name)
                    best_idx = None
                    best_rank = -1
                    for idx, ai_item in enumerate(raw_scores):
                        if idx in used_indexes:
                            continue
                        ai_key = GradingService._normalize_text(ai_item.get("criterion") or "")
                        if not ai_key:
                            continue
                        rank = -1
                        if ai_key == rubric_key:
                            rank = 3
                        elif rubric_key in ai_key:
                            rank = 2
                        elif ai_key in rubric_key:
                            rank = 1
                        if rank > best_rank:
                            best_rank = rank
                            best_idx = idx
                    return best_idx if best_rank > 0 else None

                for rubric_item in rubric_items:
                    if not isinstance(rubric_item, dict):
                        continue
                    rubric_name = str(
                        rubric_item.get("name")
                        or rubric_item.get("criteria_name")
                        or ""
                    ).strip()
                    if not rubric_name:
                        continue
                    try:
                        rubric_max = float(rubric_item.get("max_score") or 0.0)
                    except (TypeError, ValueError):
                        rubric_max = 0.0
                    if rubric_max <= 0:
                        continue

                    matched_idx = _find_best_ai_score_idx(rubric_name)
                    if matched_idx is not None:
                        used_indexes.add(matched_idx)
                        matched_item = raw_scores[matched_idx]
                        earned = max(0.0, min(float(matched_item.get("earned") or 0.0), rubric_max))
                        criteria_code = str(
                            rubric_item.get("criteria_code")
                            or rubric_item.get("criterion_code")
                            or matched_item.get("criteria_code")
                            or ""
                        ).strip()
                        feedback = matched_item.get("feedback") or "AI đã đối chiếu code theo tiêu chí này."
                        evidence = matched_item.get("evidence") or "Phân tích chuyên sâu từ AI dựa trên cấu trúc mã."
                    else:
                        earned = 0.0
                        criteria_code = str(
                            rubric_item.get("criteria_code")
                            or rubric_item.get("criterion_code")
                            or ""
                        ).strip()
                        feedback = "AI chưa tìm thấy bằng chứng đáp ứng tiêu chí này trong bài nộp."
                        evidence = "AI không tìm thấy bằng chứng đáp ứng tiêu chí này trong mã nguồn."

                    total_points += earned
                    total_max += rubric_max
                    cleaned_scores.append({
                        "criterion": rubric_name,
                        "earned": round(earned, 2),
                        "max": round(rubric_max, 2),
                        "criteria_code": criteria_code,
                        "feedback": str(feedback).strip(),
                        "evidence": str(evidence).strip(),
                    })
            else:
                for item in raw_scores:
                    earned = float(item.get("earned") or 0.0)
                    max_score = float(item.get("max") or 0.0)
                    total_points += earned
                    total_max += max_score
                    cleaned_scores.append(item)

            feedback_text = (ai_result.feedback or "").strip()
            fallback_like = "ai tạm thời không khả dụng" in feedback_text.lower() or "ước tính dự phòng" in feedback_text.lower()
            if (not feedback_text or fallback_like) and cleaned_scores:
                lines = ["### Phân tích theo tiêu chí"]
                for item in cleaned_scores:
                    detail = item.get("feedback") or "Đánh giá chuyên sâu từ trí tuệ nhân tạo."
                    lines.append(
                        f"- {item['criterion']}: {item['earned']:.2f}/{item['max']:.2f} — {detail}"
                    )
                feedback_text = "\n".join(lines)

            final = GradingService._normalize_score_10((total_points / total_max) * 10.0 if total_max > 0 else ai_score)
            final_status = "AC" if final >= 5.0 else "WA"

            ast_breakdown = ast_result.get("breakdown", {})
            breakdown = {
                "logic_score": ast_breakdown.get("tests", 0),
                "algorithm_score": ast_breakdown.get("dsa", 0),
                "style_score": ast_breakdown.get("pep8", 0),
                "optimization_score": ast_breakdown.get("complexity", 0),
            }

            ast_algos = ast_result.get("algorithms", [])
            if isinstance(ast_algos, str):
                ast_algos = [a.strip() for a in ast_algos.split(",") if a.strip()]

            combined_algos = list(set(ai_result.algorithms_detected + ast_algos))

            score_proof = {
                "mode": "ai_rubric",
                "policy_version": _SCORING_POLICY_VERSION,
                "formula": "final = sum(criteria earned) / sum(criteria max) * 10",
                "weights": {"ai": 1.0, "ast": 0.0, "algorithm": 0.0, "constraints": 0.0},
                "effective_weights": {"ai": 1.0, "ast": 0.0, "algorithm": 0.0, "constraints": 0.0},
                "components": {
                    "ai_score": ai_score,
                    "ast_score": ast_score,
                    "rubric_total_earned": round(total_points, 4),
                    "rubric_total_max": round(total_max, 4),
                    "criteria_count": len(cleaned_scores),
                },
                "raw_weighted": round(final, 4),
                "final_score": final,
            }

            rubric_snapshot = GradingService._build_rubric_snapshot(rubric_profile)
            if rubric_snapshot is not None:
                score_proof["rubric_snapshot"] = rubric_snapshot

            return GradingResult(
                filename=ai_result.filename,
                total_score=final,
                status=final_status,
                algorithms_detected=combined_algos,
                feedback=feedback_text,
                time_used=ast_result.get("runtime_ms", 0.0) / 1000.0,
                memory_used=ai_result.memory_used,
                plagiarism_detected=ai_result.plagiarism_detected,
                has_rubric=True,
                breakdown=breakdown,
                strengths=ai_result.strengths,
                weaknesses=ai_result.weaknesses,
                reasoning=ai_result.reasoning,
                improvement=ai_result.improvement,
                complexity=ast_result.get("complexity", "O(n)"),
                complexity_analysis=ai_result.complexity_analysis,
                complexity_curve=GradingService._generate_complexity_curve(ast_result.get("complexity", "O(n)")),
                optimized_code=ai_result.optimized_code,
                code=code,
                language="python",
                agent_trace=ai_result.agent_trace,
                score_proof=score_proof,
                criteria_scores=cleaned_scores,
                rubric_snapshot=rubric_snapshot,
            )

        ast_breakdown = ast_result.get("breakdown", {})
        dsa_raw = float(ast_breakdown.get("dsa", 0) or 0)
        algorithm_score = GradingService._normalize_score_10((dsa_raw / 6.0) * 10.0)

        test_results = ast_result.get("test_results", []) or []
        if test_results:
            passed = sum(1 for t in test_results if t.get("passed"))
            constraints_score = GradingService._normalize_score_10((passed / len(test_results)) * 10.0)
        else:
            # Fallback when dynamic tests are unavailable: use test component in AST breakdown.
            tests_raw = float(ast_breakdown.get("tests", 0) or 0)
            constraints_score = GradingService._normalize_score_10((tests_raw / 4.0) * 10.0)

        # In Full Authority Mode (_WEIGHT_AI=1.0), we skip confidence-based weight reduction
        confidence = 1.0 if _WEIGHT_AI >= 1.0 else GradingService._compute_ai_confidence(ai_result, ast_score, ai_score)
        effective_ai_weight = round(_WEIGHT_AI * confidence, 4)
        fixed_other_weights = _WEIGHT_ALGORITHM + _WEIGHT_CONSTRAINT
        effective_ast_weight = round(max(0.0, 1.0 - fixed_other_weights - effective_ai_weight), 4)

        weighted = (
            effective_ai_weight * ai_score
            + effective_ast_weight * ast_score
            + _WEIGHT_ALGORITHM * algorithm_score
            + _WEIGHT_CONSTRAINT * constraints_score
        )
        final = GradingService._normalize_score_10(weighted)
        final_status = "AC" if final >= 5.0 else "WA"
        score_proof = {
            "mode": "ai_exclusive_v3",
            "policy_version": _SCORING_POLICY_VERSION,
            "formula": "final = ai_score (Full Authority Mode)",
            "weights": {
                "ai": _WEIGHT_AI,
                "ast": _WEIGHT_AST,
                "algorithm": _WEIGHT_ALGORITHM,
                "constraints": _WEIGHT_CONSTRAINT,
            },
            "effective_weights": {
                "ai": effective_ai_weight,
                "ast": effective_ast_weight,
                "algorithm": _WEIGHT_ALGORITHM,
                "constraints": _WEIGHT_CONSTRAINT,
            },
            "components": {
                "ai_score": ai_score,
                "ast_score": ast_score,
                "algorithm_score": algorithm_score,
                "constraints_score": constraints_score,
                "ai_confidence": round(confidence, 4),
            },
            "raw_weighted": round(weighted, 4),
            "final_score": final,
        }

        rubric_snapshot = GradingService._build_rubric_snapshot(rubric_profile)
        if rubric_snapshot is not None:
            score_proof["rubric_snapshot"] = rubric_snapshot

        breakdown = {
            "logic_score": ast_breakdown.get("tests", 0),
            "algorithm_score": ast_breakdown.get("dsa", 0),
            "style_score": ast_breakdown.get("pep8", 0),
            "optimization_score": ast_breakdown.get("complexity", 0),
        }

        ast_algos = ast_result.get("algorithms", [])
        if isinstance(ast_algos, str):
            ast_algos = [a.strip() for a in ast_algos.split(",") if a.strip()]

        combined_algos = list(set(ai_result.algorithms_detected + ast_algos))

        # Also pass through criteria_scores from rubric_profile if AI didn't provide them
        final_criteria_scores = rubric_scores or (
            rubric_profile.get("criteria_scores_computed")
            if rubric_profile
            else None
        )

        return GradingResult(
            filename=ai_result.filename,
            total_score=final,
            status=final_status,
            algorithms_detected=combined_algos,
            feedback=ai_result.feedback,
            time_used=ast_result.get("runtime_ms", 0.0) / 1000.0,
            memory_used=ai_result.memory_used,
            plagiarism_detected=ai_result.plagiarism_detected,
            has_rubric=True,
            breakdown=breakdown,
            strengths=ai_result.strengths,
            weaknesses=ai_result.weaknesses,
            reasoning=ai_result.reasoning,
            improvement=ai_result.improvement,
            complexity=ast_result.get("complexity", "O(n)"),
            complexity_analysis=ai_result.complexity_analysis,
            complexity_curve=GradingService._generate_complexity_curve(ast_result.get("complexity", "O(n)")),
            optimized_code=ai_result.optimized_code,
            code=code,
            language="python",
            agent_trace=ai_result.agent_trace,
            score_proof=score_proof,
            criteria_scores=final_criteria_scores,
            rubric_snapshot=rubric_snapshot,
        )

    @staticmethod
    def _compute_ai_confidence(ai_result: GradingResult, ast_score: float, ai_score: float) -> float:
        """Estimate AI confidence [0..1] using trace quality and score consistency.

        Confidence drives the effective AI weight in hybrid scoring:
        - High confidence (≥0.8): AI score dominates
        - Low confidence (<0.4): AST score takes over
        """
        confidence = 1.0

        # Penalise error statuses heavily
        if ai_result.status in {"RE", "TLE", "FLAG"}:
            confidence -= 0.6

        # Penalise thin reasoning (likely a fallback or placeholder)
        reasoning = (ai_result.reasoning or "").strip()
        if len(reasoning) < 30:
            confidence -= 0.20
        elif len(reasoning) < 60:
            confidence -= 0.05

        # Penalise large score divergence between AI and AST
        score_gap = abs(ai_score - ast_score)
        if score_gap > 5:
            confidence -= 0.30
        elif score_gap > 3:
            confidence -= 0.15
        elif score_gap > 1.5:
            confidence -= 0.05

        # Penalise based on agent trace quality
        for item in ai_result.agent_trace or []:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status", "")).lower()
            stage = str(item.get("stage", "")).lower()

            if status in {"fail", "error"}:
                confidence -= 0.20
            elif status == "warn":
                confidence -= 0.10

            if stage == "fallback":
                confidence -= 0.30  # Fallback means AI didn't actually grade

        # Penalise if no criteria scores (rubric-less AI response)
        if not (ai_result.criteria_scores or []):
            confidence -= 0.05

        return max(0.0, min(1.0, round(confidence, 4)))

    @staticmethod
    def _error_result(filename: str, error: str) -> GradingResult:
        """Create result for failed grading with timestamp for audit trail."""
        return GradingResult(
            filename=filename,
            total_score=0,
            status="RE",
            algorithms_detected=[],
            feedback=f"Grading failed: {error}",
            time_used=0.0,
            memory_used=0.0,
            plagiarism_detected=False,
            code=None,
            language="python",
            score_proof={
                "mode": "error",
                "policy_version": _SCORING_POLICY_VERSION,
                "formula": "final = 0 (error path)",
                "weights": {
                    "ai": _WEIGHT_AI,
                    "ast": _WEIGHT_AST,
                    "algorithm": _WEIGHT_ALGORITHM,
                    "constraints": _WEIGHT_CONSTRAINT,
                },
                "components": {"error": 1.0},
                "raw_weighted": 0.0,
                "final_score": 0.0,
                "error_detail": str(error),
                "error_timestamp": time.time(),
            },
            rubric_snapshot=None,
        )

    @staticmethod
    def _to_dict(result: GradingResult) -> Dict[str, Any]:
        """Serialize GradingResult to dict."""
        return {
            "filename": result.filename,
            "total_score": result.total_score,
            "status": result.status,
            "algorithms_detected": result.algorithms_detected,
            "feedback": result.feedback,
            "time_used": result.time_used,
            "memory_used": result.memory_used,
            "plagiarism_detected": result.plagiarism_detected,
            "plagiarism_matches": result.plagiarism_matches,
            "has_rubric": result.has_rubric,
            "breakdown": result.breakdown,
            "complexity": result.complexity,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "reasoning": result.reasoning,
            "improvement": result.improvement,
            "complexity_analysis": result.complexity_analysis,
            "student_name": result.student_name,
            "student_id": result.student_id,
            "code": result.code,
            "language": result.language,
            "test_results": getattr(result, "test_results", []),
            "optimized_code": getattr(result, "optimized_code", None),
            "complexity_curve": getattr(result, "complexity_curve", []),
            "agent_trace": getattr(result, "agent_trace", []),
            "score_proof": getattr(result, "score_proof", None),
            "criteria_scores": getattr(result, "criteria_scores", None),
            "rubric_snapshot": getattr(result, "rubric_snapshot", None),
        }

    @staticmethod
    def _generate_complexity_curve(complexity_str: str) -> List[Dict[str, Any]]:
        """Generate dummy data points for visual complexity chart."""
        import math
        points = []
        n_values = [10, 20, 50, 100, 200, 500, 1000]
        
        # Determine actual curve type
        is_n2 = "n^2" in complexity_str or "square" in complexity_str.lower()
        is_n3 = "n^3" in complexity_str
        is_logn = "log" in complexity_str.lower()
        is_nlogn = "n log" in complexity_str.lower()

        for n in n_values:
            # Baseline (Optimal O(n) or O(log n))
            optimal_val = n if not is_logn else math.log2(n) * 10
            
            # Student's val
            if is_n3:
                student_val = (n ** 3) / 10000 
            elif is_n2:
                student_val = (n ** 2) / 100
            elif is_nlogn:
                student_val = n * math.log2(n) / 5
            elif is_logn:
                student_val = math.log2(n) * 12
            else: # O(n) or unknown
                student_val = n * 1.1 

            points.append({
                "n": n,
                "student": round(student_val, 2),
                "optimal": round(optimal_val, 2)
            })
        return points
