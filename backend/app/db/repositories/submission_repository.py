import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import desc, func, case, text
from app.db.repositories.base import BaseRepository
from app.models.models import GradingHistory, RunResult
from app.utils.security import calculate_jaccard_similarity

class SubmissionRepository(BaseRepository):
    """Core repository for grading history, test results, and analytics."""

    def save_result(self, result: Dict) -> int:
        try:
            with self.get_session() as session:
                record = GradingHistory(
                    job_id=result.get("job_id", ""),
                    student_id=result.get("student_id", ""),
                    student_name=result.get("student_name", ""),
                    assignment_code=result.get("assignment_code", ""),
                    filename=result.get("filename", ""),
                    topic=result.get("topic", ""),
                    total_score=result.get("total_score", 0),
                    algorithms=",".join(result.get("algorithms_detected", [])),
                    status=result.get("status", "AC"),
                    feedback=json.dumps(result.get("feedback", "")),
                    fingerprint=result.get("fingerprint", ""),
                    plagiarism_detected=result.get("plagiarism_detected", False),
                    plagiarism_matches=json.dumps(result.get("plagiarism_matches", [])),
                    code=result.get("code"),
                    language=result.get("language", "python"),
                    needs_review=result.get("needs_review", False),
                    score_proof=json.dumps(result.get("score_proof"), ensure_ascii=False) if result.get("score_proof") is not None else None,
                    rubric_snapshot=json.dumps(result.get("rubric_snapshot"), ensure_ascii=False) if result.get("rubric_snapshot") is not None else None,
                )
                session.add(record)
                session.flush()
                
                # Save test results if any
                test_results = result.get("test_results", [])
                if test_results:
                    for tc in test_results:
                        session.add(RunResult(
                            grading_history_id=record.id,
                            testcase_id=tc.get("testcase_id", ""),
                            stdout=tc.get("actual_output", ""),
                            stderr=tc.get("error", ""),
                            time_ms=tc.get("time_ms", 0),
                            mem_kb=tc.get("memory_kb", 0),
                            passed=tc.get("passed", False),
                            error_message=tc.get("error_message", "")
                        ))
                return record.id
        except Exception as e:
            self.logger.error("Save result failed: %s", e)
            raise

    def get_all_submissions(self, page: int = 1, page_size: int = 50, **filters) -> Dict:
        try:
            with self.get_session() as session:
                query = session.query(GradingHistory)
                if filters.get("student_id"): query = query.filter(GradingHistory.student_id == filters["student_id"])
                if filters.get("assignment_code"): query = query.filter(GradingHistory.assignment_code == filters["assignment_code"])
                if filters.get("status") and filters["status"] != "all": query = query.filter(GradingHistory.status == filters["status"])
                
                total = query.count()
                records = query.order_by(desc(GradingHistory.submitted_at)).offset((page-1)*page_size).limit(page_size).all()
                return {"submissions": [r.to_dict() for r in records], "total": total}
        except Exception as e:
            self.logger.error("Get submissions failed: %s", e)
            return {"submissions": [], "total": 0}

    def delete_submission(self, submission_id: int) -> bool:
        try:
            with self.get_session() as session:
                session.query(RunResult).filter(RunResult.grading_history_id == submission_id).delete()
                result = session.query(GradingHistory).filter(GradingHistory.id == submission_id).delete()
                return bool(result)
        except Exception as e:
            self.logger.error("Delete failed: %s", e)
            return False

    def get_by_id(self, result_id: int) -> Optional[Dict]:
        try:
            with self.get_session() as session:
                record = session.query(GradingHistory).filter(GradingHistory.id == result_id).first()
                return record.to_dict() if record else None
        except Exception as e:
            self.logger.error("Get by ID failed: %s", e)
            return None

    def get_summary_stats(self) -> Dict:
        """Optimized statistics generator using single-query aggregation."""
        try:
            with self.get_session() as session:
                score_col = func.coalesce(GradingHistory.final_score, GradingHistory.total_score)
                thirty_days_ago = datetime.now() - timedelta(days=30)

                agg = session.query(
                    func.count(GradingHistory.id).label('total'),
                    func.count(func.distinct(GradingHistory.student_id)).label('total_students'),
                    func.avg(score_col).label('avg'),
                    func.max(score_col).label('max'),
                    func.sum(case((GradingHistory.plagiarism_detected == True, 1), else_=0)).label('plag_count'),
                    func.sum(case((score_col >= 5.0, 1), else_=0)).label('pass_count')
                ).first()

                total = agg.total or 0
                return {
                    "total_submissions": total,
                    "total_students": agg.total_students or 0,
                    "avg_score": round(agg.avg, 1) if agg.avg else 0.0,
                    "max_score": agg.max or 0.0,
                    "pass_rate": round((agg.pass_count or 0) / total * 100, 1) if total > 0 else 0.0,
                    "plagiarism_count": agg.plag_count or 0
                }
        except Exception as e:
            self.logger.error("Get summary stats failed: %s", e)
            return {"error": str(e)}

    def save_batch_results(self, results: List[Dict], assignment_code: Optional[str] = None) -> List[int]:

        saved_ids = []
        for res in results:
            if assignment_code: res["assignment_code"] = assignment_code
            try:
                saved_ids.append(self.save_result(res))
            except Exception: continue
        return saved_ids

    def get_student_scores(self, student_id: str, page: int = 1, page_size: int = 20) -> Dict:
        return self.get_all_submissions(page=page, page_size=page_size, student_id=student_id)

    def get_assignment_scores(self, assignment_code: str, page: int = 1, page_size: int = 20) -> Dict:
        return self.get_all_submissions(page=page, page_size=page_size, assignment_code=assignment_code)


    def find_similar(self, fingerprint: str, threshold: float = 0.8, topic: str = None) -> List[Dict]:
        """Detect potential plagiarism using Jaccard similarity."""
        try:
            with self.get_session() as session:
                cutoff = datetime.now() - timedelta(days=90)
                query = session.query(GradingHistory).filter(
                    GradingHistory.submitted_at >= cutoff,
                    GradingHistory.fingerprint != ""
                )
                if topic: query = query.filter(GradingHistory.topic == topic)
                
                records = query.order_by(desc(GradingHistory.submitted_at)).limit(500).all()
                matches = []
                target_set = set(fingerprint.split("|")) if "|" in fingerprint else {fingerprint}
                
                for r in records:
                    source_set = set(r.fingerprint.split("|")) if "|" in r.fingerprint else {r.fingerprint}
                    similarity = calculate_jaccard_similarity(target_set, source_set)
                    if similarity >= threshold:
                        matches.append({"id": r.id, "student_name": r.student_name, "similarity": similarity})
                
                return sorted(matches, key=lambda x: x["similarity"], reverse=True)[:10]
        except Exception as e:
            self.logger.error("Similarity search failed: %s", e)
            return []

    def save_runs(self, history_id: int, runs_data: List[Dict]):
        try:
            with self.get_session() as session:
                for run_data in runs_data:
                    session.add(RunResult(
                        grading_history_id=history_id,
                        testcase_id=run_data.get("testcase_id"),
                        stdout=run_data.get("stdout", ""),
                        stderr=run_data.get("stderr", ""),
                        time_ms=run_data.get("time_ms", 0.0),
                        mem_kb=run_data.get("mem_kb", 0.0),
                        passed=run_data.get("passed", False),
                        error_message=run_data.get("error_message", "")
                    ))
        except Exception as e:
            self.logger.error("Failed to save runs: %s", e)

