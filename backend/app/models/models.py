from datetime import datetime
import json
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))
    full_name = Column(String(100))
    role = Column(String(20), default="STUDENT")
    created_at = Column(DateTime, default=datetime.now)

class GradingHistory(Base):
    """Grading history model with optimized indexes."""
    __tablename__ = "grading_history"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), index=True)
    student_id = Column(String(50), index=True)
    student_name = Column(String(255), index=True)
    assignment_code = Column(String(100), index=True)
    filename = Column(String(255))
    topic = Column(String(100))
    total_score = Column(Float, index=True)
    algorithms = Column(String(500))
    status = Column(String(50), index=True)
    feedback = Column(Text)
    # SQL Server cannot create an index on TEXT/NTEXT columns.
    fingerprint = Column(String(900), index=True)
    plagiarism_detected = Column(Boolean, default=False, index=True)
    plagiarism_matches = Column(Text)
    submitted_at = Column(DateTime, default=datetime.now, index=True)
    code = Column(Text)
    language = Column(String(20), default="python")
    final_score = Column(Float)
    needs_review = Column(Boolean, default=False, index=True)
    reviewer_id = Column(String(50), index=True)
    is_manual_grade = Column(Boolean, default=False)
    rubric_file_path = Column(String(500))
    # score_proof = Column(Text)
    # rubric_snapshot = Column(Text)
    score_proof = Column(Text)
    rubric_snapshot = Column(Text)

    __table_args__ = (
        Index('idx_student_assignment', 'student_id', 'assignment_code'),
        Index('idx_assignment_submitted', 'assignment_code', 'submitted_at'),
        Index('idx_submitted_status', 'submitted_at', 'status'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "assignment_code": self.assignment_code,
            "filename": self.filename,
            "topic": self.topic,
            "total_score": self.total_score,
            "algorithms": self.algorithms,
            "status": self.status,
            "plagiarism_detected": self.plagiarism_detected,
            "plagiarism_matches": json.loads(self.plagiarism_matches) if self.plagiarism_matches else [],
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "code": self.code,
            "language": self.language,
            "final_score": self.final_score if self.final_score is not None else self.total_score,
            "needs_review": self.needs_review,
            "reviewer_id": self.reviewer_id,
            "score_proof": json.loads(self.score_proof) if self.score_proof else None,
            "rubric_snapshot": json.loads(self.rubric_snapshot) if self.rubric_snapshot else None,
        }

class RunResult(Base):
    """Individual test run results for deeper inspection."""
    __tablename__ = "run_results"

    id = Column(Integer, primary_key=True)
    grading_history_id = Column(Integer, index=True)
    testcase_id = Column(String(100))
    stdout = Column(Text)
    stderr = Column(Text)
    time_ms = Column(Float)
    mem_kb = Column(Float)
    passed = Column(Boolean, index=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now, index=True)

class Rubric(Base):
    """Rubric model for manual grading criteria."""
    __tablename__ = "rubrics"

    id = Column(Integer, primary_key=True)
    assignment_code = Column(String(100), index=True)
    topic = Column(String(100))
    criteria_name = Column(String(200))
    max_score = Column(Float, default=10.0)
    description = Column(Text)
    file_path = Column(String(500))
    created_by = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ManualGrade(Base):
    """Manual grading records."""
    __tablename__ = "manual_grades"

    id = Column(Integer, primary_key=True)
    grading_history_id = Column(Integer, index=True)
    student_id = Column(String(50), index=True)
    assignment_code = Column(String(100), index=True)
    rubric_id = Column(Integer)
    criteria_scores = Column(Text)
    total_score = Column(Float)
    feedback = Column(Text)
    graded_by = Column(String(50), index=True)
    graded_at = Column(DateTime, default=datetime.now)
    rubric_file_path = Column(String(500))
