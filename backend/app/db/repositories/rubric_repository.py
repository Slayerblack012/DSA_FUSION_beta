import json
from typing import List, Dict, Optional
from datetime import datetime
from app.db.repositories.base import BaseRepository
from app.models.models import Rubric, ManualGrade, GradingHistory

class RubricRepository(BaseRepository):
    """Handles rubrics and manual instructor grading."""

    def create_rubric(self, assignment_code: str, topic: str, criteria_name: str, max_score: float, description: str, file_path: str, created_by: str) -> Optional[int]:
        try:
            with self.get_session() as session:
                rubric = Rubric(assignment_code=assignment_code, topic=topic, criteria_name=criteria_name, max_score=max_score, description=description, file_path=file_path, created_by=created_by)
                session.add(rubric)
                session.flush()
                return rubric.id
        except Exception as e:
            self.logger.error("Create rubric failed: %s", e)
            return None

    def get_by_assignment(self, assignment_code: str) -> List[Dict]:
        try:
            with self.get_session() as session:
                rubrics = session.query(Rubric).filter(Rubric.assignment_code == assignment_code).order_by(Rubric.created_at.desc()).all()
                return [{
                    "id": r.id, "assignment_code": r.assignment_code, "topic": r.topic,
                    "criteria_name": r.criteria_name, "max_score": r.max_score,
                    "description": r.description, "file_path": r.file_path,
                    "created_by": r.created_by, "created_at": r.created_at.isoformat() if r.created_at else None
                } for r in rubrics]
        except Exception as e:
            self.logger.error("Get rubrics failed: %s", e)
            return []

    def create_manual_grade(self, grading_history_id: int, student_id: str,
                           assignment_code: str, rubric_id: int, criteria_scores: Dict,
                           total_score: float, feedback: str, graded_by: str,
                           rubric_file_path: str = None) -> Optional[int]:
        try:
            with self.get_session() as session:
                manual_grade = ManualGrade(
                    grading_history_id=grading_history_id,
                    student_id=student_id,
                    assignment_code=assignment_code,
                    rubric_id=rubric_id,
                    criteria_scores=json.dumps(criteria_scores),
                    total_score=total_score,
                    feedback=feedback,
                    graded_by=graded_by,
                    rubric_file_path=rubric_file_path
                )
                session.add(manual_grade)
                session.flush()
                
                # Sync with history
                history = session.query(GradingHistory).filter(GradingHistory.id == grading_history_id).first()
                if history:
                    history.final_score = total_score
                    history.is_manual_grade = True
                    history.reviewer_id = graded_by
                return manual_grade.id
        except Exception as e:
            self.logger.error("Create manual grade failed: %s", e)
            return None
